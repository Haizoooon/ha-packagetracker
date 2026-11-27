"""Device triggers for native Home Assistant automation editing."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_PACKAGE_ID,
    DOMAIN,
    EVENT_PACKAGE_FOUND,
    EVENT_STATUS_MAP,
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
)

TRIGGER_TYPES: dict[str, str] = {
    "package_found": EVENT_PACKAGE_FOUND,
    "package_ordered": EVENT_STATUS_MAP[STATUS_ORDERED],
    "package_shipped": EVENT_STATUS_MAP[STATUS_SHIPPED],
    "package_in_transit": EVENT_STATUS_MAP[STATUS_IN_TRANSIT],
    "package_out_for_delivery": EVENT_STATUS_MAP[STATUS_OUT_FOR_DELIVERY],
    "package_delivered": EVENT_STATUS_MAP[STATUS_DELIVERED],
    "package_delayed": EVENT_STATUS_MAP[STATUS_DELAYED],
    "package_ready_for_pickup": EVENT_STATUS_MAP[STATUS_READY_FOR_PICKUP],
    "package_returned": EVENT_STATUS_MAP[STATUS_RETURNED],
    "package_cancelled": EVENT_STATUS_MAP[STATUS_CANCELLED],
}

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required("platform"): "device",
        vol.Required("domain"): DOMAIN,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required("type"): vol.In(
            {**{key: key for key in TRIGGER_TYPES}, "package_status_changed": "status"}
        ),
        vol.Optional(ATTR_PACKAGE_ID): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def _device_belongs_to_integration(hass: HomeAssistant, device_id: str) -> bool:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return False
    return any(
        identifier[0] == DOMAIN for identifier in device.identifiers
    )


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    if not _device_belongs_to_integration(hass, device_id):
        return []
    triggers: list[dict[str, Any]] = []
    for trigger_type in TRIGGER_TYPES:
        triggers.append(
            {
                "platform": "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "type": trigger_type,
                "metadata": {},
            }
        )
    triggers.append(
        {
            "platform": "device",
            "domain": DOMAIN,
            "device_id": device_id,
            "type": "package_status_changed",
            "metadata": {},
        }
    )
    return triggers


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    return {
        "extra_fields": vol.Schema(
            {vol.Optional(ATTR_PACKAGE_ID): cv.string}
        )
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    trigger_type = config["type"]
    package_id = config.get(ATTR_PACKAGE_ID)
    if trigger_type == "package_status_changed":
        event_types = list(EVENT_STATUS_MAP.values())
    else:
        event_type = TRIGGER_TYPES.get(trigger_type)
        event_types = [event_type] if event_type else []

    unsubs: list[CALLBACK_TYPE] = []
    for event_type in event_types:
        event_data = {"package_id": package_id} if package_id else {}
        unsubs.append(
            await event_trigger.async_attach_trigger(
                hass,
                event_trigger.TRIGGER_SCHEMA(
                    {
                        event_trigger.CONF_PLATFORM: "event",
                        event_trigger.CONF_EVENT_TYPE: event_type,
                        event_trigger.CONF_EVENT_DATA: event_data,
                    }
                ),
                action,
                trigger_info,
                platform_type="device",
            )
        )

    @callback
    def _unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    return _unsubscribe
