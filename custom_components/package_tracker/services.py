"""Home Assistant actions for Package Tracker."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ALL_CARRIERS,
    ALL_STATUSES,
    ATTR_ENTRY_ID,
    ATTR_PACKAGE_ID,
    CARRIER_NAMES,
    CONF_CARRIER,
    CONF_COMPLETED,
    CONF_CONFIRM,
    CONF_DELIVERED_AT,
    CONF_DELIVERY_WINDOW,
    CONF_EXPECTED_DELIVERY,
    CONF_INCLUDE_COMPLETED,
    CONF_MERCHANT,
    CONF_NOTES,
    CONF_ORDER_NUMBER,
    CONF_PRODUCT_NAME,
    CONF_RESET_SYNC,
    CONF_STATUS,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    SERVICE_DELETE_ALL,
    SERVICE_DELETE_PACKAGE,
    SERVICE_DISCONNECT,
    SERVICE_GET_PACKAGES,
    SERVICE_MARK_COMPLETED,
    SERVICE_MARK_DELIVERED,
    SERVICE_REFRESH,
    SERVICE_REFRESH_TRACKING,
    SERVICE_SYNC,
    SERVICE_UPDATE_PACKAGE,
)
from .runtime import EntryRuntime, get_runtime, get_runtimes

_LOGGER = logging.getLogger(__name__)

SERVICES_KEY = f"{DOMAIN}_services_registered"

SERVICE_SYNC_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_ENTRY_ID): cv.string}
)
SERVICE_REFRESH_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_ENTRY_ID): cv.string}
)
SERVICE_REFRESH_TRACKING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(ATTR_PACKAGE_ID): cv.string,
    }
)
SERVICE_MARK_DELIVERED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PACKAGE_ID): cv.string,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(CONF_DELIVERED_AT): cv.date,
    }
)
SERVICE_MARK_COMPLETED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PACKAGE_ID): cv.string,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(CONF_COMPLETED, default=True): cv.boolean,
    }
)
SERVICE_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PACKAGE_ID): cv.string,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(CONF_MERCHANT): cv.string,
        vol.Optional(CONF_PRODUCT_NAME): cv.string,
        vol.Optional(CONF_CARRIER): cv.string,
        vol.Optional(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_ORDER_NUMBER): cv.string,
        vol.Optional(CONF_EXPECTED_DELIVERY): cv.date,
        vol.Optional(CONF_DELIVERY_WINDOW): cv.string,
        vol.Optional(CONF_STATUS): vol.In(ALL_STATUSES),
        vol.Optional(CONF_NOTES): cv.string,
        vol.Optional(CONF_COMPLETED): cv.boolean,
    }
)
SERVICE_DELETE_PACKAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PACKAGE_ID): cv.string,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)
SERVICE_DELETE_ALL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIRM): cv.boolean,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(CONF_RESET_SYNC, default=False): cv.boolean,
    }
)
SERVICE_DISCONNECT_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_ENTRY_ID): cv.string}
)
SERVICE_GET_PACKAGES_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional(CONF_STATUS): vol.In(ALL_STATUSES),
        vol.Optional(CONF_MERCHANT): cv.string,
        vol.Optional(CONF_INCLUDE_COMPLETED, default=True): cv.boolean,
    }
)


def _runtimes_for_call(hass: HomeAssistant, entry_id: str | None) -> list[EntryRuntime]:
    if entry_id:
        runtime = get_runtime(hass, entry_id)
        if runtime is None:
            raise HomeAssistantError(f"Package Tracker Eintrag {entry_id} nicht gefunden")
        return [runtime]
    runtimes = list(get_runtimes(hass).values())
    if not runtimes:
        raise HomeAssistantError("Package Tracker ist nicht eingerichtet")
    return runtimes


def _runtime_for_package(
    hass: HomeAssistant, package_id: str, entry_id: str | None
) -> EntryRuntime:
    candidates = _runtimes_for_call(hass, entry_id)
    for runtime in candidates:
        if runtime.manager.get_shipment(package_id) is not None:
            return runtime
    raise HomeAssistantError(f"Paket {package_id} nicht gefunden")


def _canonical_carrier(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().casefold()
    if lowered in ALL_CARRIERS:
        return lowered
    for key, name in CARRIER_NAMES.items():
        if name.casefold() == lowered:
            return key
    raise HomeAssistantError(f"Unbekannter Paketdienst: {value}")


async def async_setup_services(hass: HomeAssistant) -> None:
    if hass.data.get(SERVICES_KEY):
        return
    hass.data[SERVICES_KEY] = True

    async def async_handle_sync(call: ServiceCall) -> dict[str, Any]:
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        results: dict[str, Any] = {}
        for runtime in runtime_list:
            results[runtime.entry.entry_id] = await runtime.coordinator.async_manual_sync()
        if len(results) == 1:
            return next(iter(results.values()))
        return {"ok": True, "entries": results}

    async def async_handle_refresh(call: ServiceCall) -> dict[str, Any]:
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        for runtime in runtime_list:
            await runtime.coordinator.async_apply_changes([])
        return {"ok": True, "entries": len(runtime_list)}

    async def async_handle_refresh_tracking(call: ServiceCall) -> dict[str, Any]:
        package_id = call.data.get(ATTR_PACKAGE_ID)
        if package_id:
            runtime = _runtime_for_package(
                hass, package_id, call.data.get(ATTR_ENTRY_ID)
            )
            changes = await runtime.coordinator.async_refresh_tracking_now(package_id)
            return {"ok": True, "updated": len(changes)}
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        total = 0
        for runtime in runtime_list:
            changes = await runtime.coordinator.async_refresh_tracking_now()
            total += len(changes)
        return {"ok": True, "updated": total}

    async def async_handle_mark_delivered(call: ServiceCall) -> dict[str, Any]:
        package_id = call.data[ATTR_PACKAGE_ID]
        runtime = _runtime_for_package(hass, package_id, call.data.get(ATTR_ENTRY_ID))
        delivered_at = call.data.get(CONF_DELIVERED_AT)
        change = await runtime.coordinator.async_mark_delivered(
            package_id,
            delivered_at.isoformat() if delivered_at else None,
        )
        if change is None:
            raise HomeAssistantError("Paket ist bereits zugestellt oder nicht vorhanden")
        return {"ok": True, "package_id": package_id, "status": change.new_status}

    async def async_handle_mark_completed(call: ServiceCall) -> dict[str, Any]:
        package_id = call.data[ATTR_PACKAGE_ID]
        runtime = _runtime_for_package(hass, package_id, call.data.get(ATTR_ENTRY_ID))
        completed = bool(call.data.get(CONF_COMPLETED, True))
        await runtime.coordinator.async_mark_completed(package_id, completed)
        return {"ok": True, "package_id": package_id, "completed": completed}

    async def async_handle_update(call: ServiceCall) -> dict[str, Any]:
        package_id = call.data[ATTR_PACKAGE_ID]
        runtime = _runtime_for_package(hass, package_id, call.data.get(ATTR_ENTRY_ID))
        fields: dict[str, Any] = {}
        for key in (
            CONF_MERCHANT,
            CONF_PRODUCT_NAME,
            CONF_TRACKING_NUMBER,
            CONF_ORDER_NUMBER,
            CONF_DELIVERY_WINDOW,
            CONF_STATUS,
            CONF_NOTES,
            CONF_COMPLETED,
        ):
            if key in call.data:
                fields[key] = call.data[key]
        if CONF_CARRIER in call.data:
            fields[CONF_CARRIER] = _canonical_carrier(call.data[CONF_CARRIER])
        if CONF_EXPECTED_DELIVERY in call.data:
            fields[CONF_EXPECTED_DELIVERY] = call.data[CONF_EXPECTED_DELIVERY].isoformat()
        await runtime.coordinator.async_update_package(package_id, **fields)
        return {"ok": True, "package_id": package_id}

    async def async_handle_delete(call: ServiceCall) -> dict[str, Any]:
        package_id = call.data[ATTR_PACKAGE_ID]
        runtime = _runtime_for_package(hass, package_id, call.data.get(ATTR_ENTRY_ID))
        deleted = await runtime.coordinator.async_delete_package(package_id)
        if not deleted:
            raise HomeAssistantError(f"Paket {package_id} konnte nicht gelöscht werden")
        return {"ok": True, "package_id": package_id}

    async def async_handle_delete_all(call: ServiceCall) -> dict[str, Any]:
        if not call.data.get(CONF_CONFIRM):
            raise HomeAssistantError(
                "Löschen abgebrochen: 'confirm: true' ist erforderlich"
            )
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        for runtime in runtime_list:
            await runtime.coordinator.async_delete_all(
                reset_sync=bool(call.data.get(CONF_RESET_SYNC, False))
            )
        return {"ok": True, "entries": len(runtime_list)}

    async def async_handle_disconnect(call: ServiceCall) -> dict[str, Any]:
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        if len(runtime_list) > 1:
            raise HomeAssistantError(
                "Mehrere Konten verbunden; bitte config_entry_id angeben"
            )
        entry = runtime_list[0].entry
        await hass.config_entries.async_remove(entry.entry_id)
        return {"ok": True, "entry_id": entry.entry_id}

    async def async_handle_get_packages(call: ServiceCall) -> dict[str, Any]:
        runtime_list = _runtimes_for_call(hass, call.data.get(ATTR_ENTRY_ID))
        status_filter = call.data.get(CONF_STATUS)
        merchant_filter = call.data.get(CONF_MERCHANT)
        include_completed = call.data.get(CONF_INCLUDE_COMPLETED, True)
        packages: list[dict[str, Any]] = []
        orders: list[dict[str, Any]] = []
        for runtime in runtime_list:
            snapshot = runtime.manager.snapshot(dt_util.utcnow())
            for package in snapshot["packages"]:
                if not include_completed and package.get("completed"):
                    continue
                if status_filter and package.get("status") != status_filter:
                    continue
                if merchant_filter:
                    merchant = (package.get("merchant") or "").casefold()
                    if merchant_filter.casefold() not in merchant:
                        continue
                package["config_entry_id"] = runtime.entry.entry_id
                packages.append(package)
            orders.extend(snapshot["orders"])
        packages.sort(
            key=lambda item: (
                item.get("is_terminal", False),
                item.get("expected_delivery") or "9999-12-31",
            )
        )
        return {
            "packages": packages,
            "orders": orders,
            "count": len(packages),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC,
        async_handle_sync,
        schema=SERVICE_SYNC_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        async_handle_refresh,
        schema=SERVICE_REFRESH_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_TRACKING,
        async_handle_refresh_tracking,
        schema=SERVICE_REFRESH_TRACKING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_DELIVERED,
        async_handle_mark_delivered,
        schema=SERVICE_MARK_DELIVERED_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_COMPLETED,
        async_handle_mark_completed,
        schema=SERVICE_MARK_COMPLETED_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_PACKAGE,
        async_handle_update,
        schema=SERVICE_UPDATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_PACKAGE,
        async_handle_delete,
        schema=SERVICE_DELETE_PACKAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ALL,
        async_handle_delete_all,
        schema=SERVICE_DELETE_ALL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISCONNECT,
        async_handle_disconnect,
        schema=SERVICE_DISCONNECT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PACKAGES,
        async_handle_get_packages,
        schema=SERVICE_GET_PACKAGES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    if not hass.data.get(SERVICES_KEY):
        return
    for service in (
        SERVICE_SYNC,
        SERVICE_REFRESH,
        SERVICE_REFRESH_TRACKING,
        SERVICE_MARK_DELIVERED,
        SERVICE_MARK_COMPLETED,
        SERVICE_UPDATE_PACKAGE,
        SERVICE_DELETE_PACKAGE,
        SERVICE_DELETE_ALL,
        SERVICE_DISCONNECT,
        SERVICE_GET_PACKAGES,
    ):
        hass.services.async_remove(DOMAIN, service)
    hass.data.pop(SERVICES_KEY, None)
