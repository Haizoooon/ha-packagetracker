"""Shared entity base classes."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import PackageTrackerCoordinator


class PackageTrackerEntity(CoordinatorEntity[PackageTrackerCoordinator]):
    """Base entity bound to the single Package Tracker device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    _suggested_object_id: str | None = None

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def suggested_object_id(self) -> str | None:
        """Stable, English entity IDs independent of the UI language."""
        return self._suggested_object_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=NAME,
            manufacturer=NAME,
            model="Gmail",
            entry_type=DeviceEntryType.SERVICE,
            sw_version=VERSION,
        )
