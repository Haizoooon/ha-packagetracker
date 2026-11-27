"""Binary sensors for Package Tracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STATUS_DELAYED, STATUS_OUT_FOR_DELIVERY
from .coordinator import PackageTrackerCoordinator
from .entity import PackageTrackerEntity
from .runtime import get_runtime


def _packages(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    return (data or {}).get("packages", []) or []


def _active(package: dict[str, Any]) -> bool:
    return not package.get("is_terminal") and not package.get("completed")


@dataclass(frozen=True, kw_only=True)
class PackageTrackerBinaryDescription(BinarySensorEntityDescription):
    suggested_object_id: str | None = None
    value_fn: Callable[[dict[str, Any]], bool] = lambda data: False
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


def _packages_attr(predicate: Callable[[dict[str, Any]], bool]):
    def _fn(data: dict[str, Any]) -> dict[str, Any]:
        packages = [
            {
                "id": package.get("id"),
                "merchant": package.get("merchant"),
                "product_name": package.get("product_name"),
                "status": package.get("status"),
                "expected_delivery": package.get("expected_delivery"),
                "delivery_window": package.get("delivery_window"),
                "tracking_url": package.get("tracking_url"),
            }
            for package in _packages(data)
            if predicate(package)
        ]
        return {"count": len(packages), "packages": packages}

    return _fn


BINARY_DESCRIPTIONS: tuple[PackageTrackerBinaryDescription, ...] = (
    PackageTrackerBinaryDescription(
        key="delivery_today",
        translation_key="delivery_today",
        suggested_object_id="delivery_today",
        icon="mdi:calendar-today",
        value_fn=lambda data: any(
            package.get("expected_delivery") == dt_util.now().date().isoformat()
            and _active(package)
            for package in _packages(data)
        ),
        attributes_fn=_packages_attr(
            lambda package: package.get("expected_delivery")
            == dt_util.now().date().isoformat()
            and _active(package)
        ),
    ),
    PackageTrackerBinaryDescription(
        key="out_for_delivery",
        translation_key="out_for_delivery",
        suggested_object_id="package_out_for_delivery",
        icon="mdi:truck-delivery",
        value_fn=lambda data: any(
            package.get("status") == STATUS_OUT_FOR_DELIVERY and _active(package)
            for package in _packages(data)
        ),
        attributes_fn=_packages_attr(
            lambda package: package.get("status") == STATUS_OUT_FOR_DELIVERY
            and _active(package)
        ),
    ),
    PackageTrackerBinaryDescription(
        key="delayed",
        translation_key="delayed",
        suggested_object_id="delayed",
        icon="mdi:package-variant-closed-remove",
        value_fn=lambda data: any(
            package.get("status") == STATUS_DELAYED and _active(package)
            for package in _packages(data)
        ),
        attributes_fn=_packages_attr(
            lambda package: package.get("status") == STATUS_DELAYED
            and _active(package)
        ),
    ),
    PackageTrackerBinaryDescription(
        key="gmail_connected",
        translation_key="gmail_connected",
        suggested_object_id="gmail_connected",
        icon="mdi:gmail",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: bool((data or {}).get("gmail", {}).get("connected")),
        attributes_fn=lambda data: {
            "account": (data or {}).get("gmail", {}).get("account"),
            "last_sync": (data or {}).get("gmail", {}).get("last_sync"),
            "emails_processed": (data or {}).get("gmail", {}).get("emails_processed", 0),
        },
    ),
)


class PackageTrackerBinarySensor(PackageTrackerEntity, BinarySensorEntity):
    entity_description: PackageTrackerBinaryDescription

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        entry: ConfigEntry,
        description: PackageTrackerBinaryDescription,
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

    @property
    def is_on(self) -> bool:
        return bool(self.entity_description.value_fn(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attributes_fn(self.coordinator.data or {})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = get_runtime(hass, entry.entry_id)
    if runtime is None:
        return
    async_add_entities(
        PackageTrackerBinarySensor(runtime.coordinator, entry, description)
        for description in BINARY_DESCRIPTIONS
    )
