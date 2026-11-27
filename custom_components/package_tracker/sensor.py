"""Sensors for Package Tracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_LABELS,
    STATUS_LABELS_DE,
)
from .coordinator import PackageTrackerCoordinator
from .entity import PackageTrackerEntity
from .notifications import package_unique_id
from .runtime import get_runtime
from .util import carrier_name, parse_iso, slugify


@dataclass(frozen=True, kw_only=True)
class PackageTrackerSensorDescription(SensorEntityDescription):
    """Description for one aggregate sensor."""

    suggested_object_id: str | None = None
    value_fn: Callable[[dict[str, Any]], Any] = lambda data: None
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


def _stats(data: dict[str, Any] | None) -> dict[str, Any]:
    return (data or {}).get("stats", {}) or {}


def _packages(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    return (data or {}).get("packages", []) or []


def _compact(package: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "merchant",
        "carrier",
        "carrier_name",
        "product_name",
        "product_image",
        "order_number",
        "tracking_number",
        "tracking_url",
        "status",
        "status_label",
        "expected_delivery",
        "delivery_window",
        "actual_delivery",
        "completed",
        "is_terminal",
    )
    return {key: package.get(key) for key in keys}


def _packages_attr(
    predicate: Callable[[dict[str, Any]], bool]
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _fn(data: dict[str, Any]) -> dict[str, Any]:
        packages = [_compact(package) for package in _packages(data) if predicate(package)]
        return {"count": len(packages), "packages": packages}

    return _fn


def _main_attributes(data: dict[str, Any]) -> dict[str, Any]:
    stats = dict(_stats(data))
    next_delivery = stats.get("next_delivery")
    if isinstance(next_delivery, dict):
        stats["next_delivery"] = _compact(next_delivery)
    return {
        "counts": stats,
        "packages": [_compact(package) for package in _packages(data)],
        "gmail": (data or {}).get("gmail", {}),
        "sync": (data or {}).get("sync", {}),
        "updated_at": (data or {}).get("generated_at"),
    }


def _next_attributes(data: dict[str, Any]) -> dict[str, Any]:
    next_delivery = _stats(data).get("next_delivery")
    if not isinstance(next_delivery, dict):
        return {"package": None}
    return {
        "package": _compact(next_delivery),
        "product_name": next_delivery.get("product_name"),
        "merchant": next_delivery.get("merchant"),
        "carrier": next_delivery.get("carrier"),
        "carrier_name": carrier_name(next_delivery.get("carrier")),
        "delivery_window": next_delivery.get("delivery_window"),
        "tracking_url": next_delivery.get("tracking_url"),
    }


SENSOR_DESCRIPTIONS: tuple[PackageTrackerSensorDescription, ...] = (
    PackageTrackerSensorDescription(
        key="packages",
        translation_key="packages",
        suggested_object_id="packages",
        icon="mdi:package-variant-closed",
        value_fn=lambda data: _stats(data).get("active", 0),
        attributes_fn=_main_attributes,
    ),
    PackageTrackerSensorDescription(
        key="deliveries_today",
        translation_key="deliveries_today",
        suggested_object_id="deliveries_today",
        icon="mdi:calendar-today",
        value_fn=lambda data: _stats(data).get("delivery_today", 0),
        attributes_fn=_packages_attr(
            lambda package: package.get("expected_delivery")
            == dt_util.now().date().isoformat()
            and not package.get("is_terminal")
            and not package.get("completed")
        ),
    ),
    PackageTrackerSensorDescription(
        key="next_delivery",
        translation_key="next_delivery",
        suggested_object_id="next_delivery",
        icon="mdi:truck-delivery",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: _stats(data).get("next_delivery", {}).get("expected_delivery")
        if isinstance(_stats(data).get("next_delivery"), dict)
        else None,
        attributes_fn=_next_attributes,
    ),
    PackageTrackerSensorDescription(
        key="delivered_today",
        translation_key="delivered_today",
        suggested_object_id="delivered_today",
        icon="mdi:package-variant",
        value_fn=lambda data: _stats(data).get("delivered_today", 0),
        attributes_fn=_packages_attr(
            lambda package: package.get("status") == STATUS_DELIVERED
            and package.get("actual_delivery") == dt_util.now().date().isoformat()
        ),
    ),
    PackageTrackerSensorDescription(
        key="packages_in_transit",
        translation_key="packages_in_transit",
        suggested_object_id="packages_in_transit",
        icon="mdi:truck-fast",
        value_fn=lambda data: _stats(data).get("in_transit", 0),
        attributes_fn=_packages_attr(
            lambda package: package.get("status")
            in {"shipped", "in_transit", "out_for_delivery", "delayed"}
            and not package.get("is_terminal")
            and not package.get("completed")
        ),
    ),
    PackageTrackerSensorDescription(
        key="delayed",
        translation_key="delayed",
        suggested_object_id="delayed",
        icon="mdi:package-variant-closed-remove",
        value_fn=lambda data: _stats(data).get("delayed", 0),
        attributes_fn=_packages_attr(
            lambda package: package.get("status") == STATUS_DELAYED
            and not package.get("is_terminal")
            and not package.get("completed")
        ),
    ),
    PackageTrackerSensorDescription(
        key="last_sync",
        translation_key="last_sync",
        suggested_object_id="last_sync",
        icon="mdi:email-sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: (data or {}).get("gmail", {}).get("last_sync"),
        attributes_fn=lambda data: {
            "emails_processed": (data or {}).get("gmail", {}).get("emails_processed", 0),
            "connected": (data or {}).get("gmail", {}).get("connected", False),
            "account": (data or {}).get("gmail", {}).get("account"),
        },
    ),
)


class PackageTrackerSensor(PackageTrackerEntity, SensorEntity):
    """Aggregate sensor backed by the coordinator snapshot."""

    entity_description: PackageTrackerSensorDescription

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        entry: ConfigEntry,
        description: PackageTrackerSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._suggested_object_id = (
            description.suggested_object_id or description.key
        )
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def native_value(self) -> Any:
        value = self.entity_description.value_fn(self.coordinator.data or {})
        if self.entity_description.device_class == SensorDeviceClass.DATE:
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value[:10])
                except ValueError:
                    return None
            return None
        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            if isinstance(value, str):
                return parse_iso(value)
            return value
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attributes_fn(self.coordinator.data or {})


class PackageStatusSensor(PackageTrackerEntity, SensorEntity):
    """One sensor per recognised package, with the full detail payload."""

    _attr_icon = "mdi:package-variant-closed"
    _attr_native_unit_of_measurement = None

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        entry: ConfigEntry,
        package_id: str,
        *,
        on_remove: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(coordinator, entry)
        self._package_id = package_id
        self._remove_callback = on_remove
        self._removal_scheduled = False
        self._attr_unique_id = package_unique_id(package_id)
        shipment = coordinator.manager.get_shipment(package_id)
        merchant = shipment.merchant if shipment else None
        self._suggested_object_id = (
            f"package_{slugify(merchant, 'unknown')}_{package_id[-8:]}"
        )

    @property
    def _shipment(self):
        return self.coordinator.manager.get_shipment(self._package_id)

    @property
    def name(self) -> str:
        shipment = self._shipment
        if shipment is None:
            return "Parcel"
        if shipment.product_name:
            return shipment.product_name
        german = str(self.hass.config.language).lower().startswith("de")
        if shipment.merchant:
            return (
                f"Paket von {shipment.merchant}"
                if german
                else f"Parcel from {shipment.merchant}"
            )
        return "Paket" if german else "Parcel"

    @property
    def available(self) -> bool:
        return super().available and self._shipment is not None

    @property
    def native_value(self) -> str | None:
        shipment = self._shipment
        return shipment.status if shipment is not None else None

    @property
    def icon(self) -> str:
        shipment = self._shipment
        if shipment is None:
            return "mdi:package-variant-closed"
        return {
            "ordered": "mdi:cart-outline",
            "shipped": "mdi:package-variant",
            "in_transit": "mdi:truck-fast",
            "out_for_delivery": "mdi:truck-delivery",
            "delivered": "mdi:package-variant-closed-check",
            "delayed": "mdi:package-variant-closed-remove",
            "ready_for_pickup": "mdi:package-variant-closed-check",
            "returned": "mdi:package-variant-closed-remove",
            "cancelled": "mdi:close-circle-outline",
        }.get(shipment.status, "mdi:package-variant-closed")

    @property
    def entity_picture(self) -> str | None:
        shipment = self._shipment
        return shipment.product_image if shipment is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        payload = self.coordinator.manager.package_payload(self._package_id)
        if payload is None:
            return {"package_id": self._package_id, "available": False}
        payload["package_id"] = self._package_id
        labels = (
            STATUS_LABELS_DE
            if str(self.hass.config.language).lower().startswith("de")
            else STATUS_LABELS
        )
        payload["status_label"] = labels.get(
            payload.get("status", ""), payload.get("status")
        )
        payload["config_entry_id"] = self._entry.entry_id
        return payload

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._shipment is None:
            if not self._removal_scheduled:
                self._removal_scheduled = True
                self.hass.async_create_task(self._async_remove_missing())
            return
        super()._handle_coordinator_update()

    async def _async_remove_missing(self) -> None:
        if self._remove_callback is not None:
            self._remove_callback(self._package_id)
        await self.async_remove(force_remove=True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = get_runtime(hass, entry.entry_id)
    if runtime is None:
        return
    coordinator = runtime.coordinator
    known: set[str] = set()

    @callback
    def _add_new_packages() -> None:
        current = set(runtime.manager.shipments)
        new_ids = current - known
        if not new_ids:
            return
        known.update(new_ids)
        async_add_entities(
            PackageStatusSensor(
                coordinator,
                entry,
                package_id,
                on_remove=known.discard,
            )
            for package_id in sorted(new_ids)
        )

    async_add_entities(
        PackageTrackerSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )
    _add_new_packages()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_packages))
