"""Device conditions for native automation editing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    ALL_CARRIERS,
    ALL_STATUSES,
    ATTR_PACKAGE_ID,
    DOMAIN,
    TERMINAL_STATUSES,
)
from .runtime import get_runtime
from .util import carrier_name, normalize_key

CONDITION_TYPES = (
    "package_status",
    "carrier_is",
    "merchant_is",
    "product_contains",
    "delivery_today",
    "package_exists",
)

CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required("condition"): "device",
        vol.Required("domain"): DOMAIN,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required("type"): vol.In(CONDITION_TYPES),
        vol.Optional(ATTR_PACKAGE_ID): cv.string,
        vol.Optional("status"): vol.In(ALL_STATUSES),
        vol.Optional("carrier"): cv.string,
        vol.Optional("merchant"): cv.string,
        vol.Optional("text"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def _device_belongs_to_integration(hass: HomeAssistant, device_id: str) -> bool:
    device = dr.async_get(hass).async_get(device_id)
    return bool(
        device and any(identifier[0] == DOMAIN for identifier in device.identifiers)
    )


async def async_get_conditions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    if not _device_belongs_to_integration(hass, device_id):
        return []
    return [
        {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": device_id,
            "type": condition_type,
            "metadata": {},
        }
        for condition_type in CONDITION_TYPES
    ]


def _shipments(runtime: Any, package_id: str | None):
    if package_id:
        shipment = runtime.manager.get_shipment(package_id)
        return [shipment] if shipment else []
    return [s for s in runtime.manager.iter_shipments() if not s.completed]


async def async_get_condition_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    condition_type = config.get("type")
    fields: dict[Any, Any] = {}
    if condition_type == "package_status":
        fields[vol.Required("status")] = vol.In(ALL_STATUSES)
    elif condition_type == "carrier_is":
        fields[vol.Required("carrier")] = vol.In(ALL_CARRIERS)
    elif condition_type == "merchant_is":
        fields[vol.Required("merchant")] = cv.string
    elif condition_type == "product_contains":
        fields[vol.Required("text")] = cv.string
    fields[vol.Optional(ATTR_PACKAGE_ID)] = cv.string
    return {"extra_fields": vol.Schema(fields)}


def _runtime_for_device(hass: HomeAssistant, device_id: str):
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry_id in device.config_entries:
        runtime = get_runtime(hass, entry_id)
        if runtime is not None:
            return runtime
    return None


def async_condition_from_config(
    hass: HomeAssistant, config: ConfigType
) -> Callable[[HomeAssistant, dict[str, Any]], bool]:
    runtime = _runtime_for_device(hass, config[CONF_DEVICE_ID])
    condition_type = config["type"]
    package_id = config.get(ATTR_PACKAGE_ID)
    status = config.get("status")
    carrier = config.get("carrier")
    merchant = config.get("merchant")
    text = config.get("text")

    def _condition(hass: HomeAssistant, variables: dict[str, Any]) -> bool:
        if runtime is None:
            return False
        shipments = _shipments(runtime, package_id)
        if condition_type == "package_exists":
            return bool(shipments)
        if condition_type == "delivery_today":
            today = dt_util.now().date().isoformat()
            return any(
                shipment.expected_delivery == today
                and shipment.status not in TERMINAL_STATUSES
                for shipment in shipments
            )
        if condition_type == "package_status":
            return any(shipment.status == status for shipment in shipments)
        if condition_type == "carrier_is" and carrier:
            wanted = normalize_key(carrier)
            return any(
                shipment.carrier == carrier
                or normalize_key(shipment.carrier) == wanted
                or normalize_key(carrier_name(shipment.carrier)) == wanted
                for shipment in shipments
            )
        if condition_type == "merchant_is" and merchant:
            wanted = normalize_key(merchant)
            return any(
                normalize_key(shipment.merchant) == wanted for shipment in shipments
            )
        if condition_type == "product_contains" and text:
            needle = text.casefold()
            return any(
                needle in (name or "").casefold()
                for shipment in shipments
                for name in [shipment.product_name, *shipment.product_names]
            )
        return False

    return _condition
