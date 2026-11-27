"""Device actions for native automation editing."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_PACKAGE_ID,
    CONF_COMPLETED,
    DOMAIN,
    SERVICE_DELETE_PACKAGE,
    SERVICE_MARK_COMPLETED,
    SERVICE_MARK_DELIVERED,
    SERVICE_REFRESH_TRACKING,
    SERVICE_SYNC,
)
from .runtime import get_runtime

ACTION_TYPES = (
    "sync",
    "refresh_tracking",
    "mark_delivered",
    "mark_completed",
    "delete_package",
)

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): "device",
        vol.Required("domain"): DOMAIN,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required("type"): vol.In(ACTION_TYPES),
        vol.Optional(ATTR_PACKAGE_ID): cv.string,
        vol.Optional(CONF_COMPLETED): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)


def _runtime_for_device(hass: HomeAssistant, device_id: str):
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry_id in device.config_entries:
        runtime = get_runtime(hass, entry_id)
        if runtime is not None:
            return runtime
    return None


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    runtime = _runtime_for_device(hass, device_id)
    if runtime is None:
        return []
    return [
        {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": device_id,
            "type": action_type,
            "metadata": {},
        }
        for action_type in ACTION_TYPES
    ]


async def async_get_action_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    runtime = _runtime_for_device(hass, config[CONF_DEVICE_ID])
    fields: dict[Any, Any] = {}
    if config.get("type") in {
        "mark_delivered",
        "mark_completed",
        "delete_package",
    }:
        options = {}
        if runtime is not None:
            for shipment in runtime.manager.iter_shipments():
                options[shipment.id] = shipment.label
        fields[vol.Required(ATTR_PACKAGE_ID)] = (
            vol.In(options) if options else cv.string
        )
    if config.get("type") == "mark_completed":
        fields[vol.Optional(CONF_COMPLETED, default=True)] = cv.boolean
    return {"extra_fields": vol.Schema(fields)}


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: dict[str, Any],
    context: Context | None,
) -> None:
    action_type = config["type"]
    data: dict[str, Any] = {}
    if config.get(ATTR_PACKAGE_ID):
        data[ATTR_PACKAGE_ID] = config[ATTR_PACKAGE_ID]
    if config.get(CONF_COMPLETED) is not None:
        data[CONF_COMPLETED] = config[CONF_COMPLETED]

    service = {
        "sync": SERVICE_SYNC,
        "refresh_tracking": SERVICE_REFRESH_TRACKING,
        "mark_delivered": SERVICE_MARK_DELIVERED,
        "mark_completed": SERVICE_MARK_COMPLETED,
        "delete_package": SERVICE_DELETE_PACKAGE,
    }.get(action_type)
    if service is None:
        return
    await hass.services.async_call(
        DOMAIN,
        service,
        data,
        blocking=True,
        context=context,
    )
