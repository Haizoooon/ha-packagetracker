"""Buttons for manual actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TRACKING_PROVIDER,
    DOMAIN,
    TRACKING_PROVIDER_NONE,
)
from .coordinator import PackageTrackerCoordinator
from .entity import PackageTrackerEntity
from .runtime import get_runtime


class PackageTrackerButton(PackageTrackerEntity, ButtonEntity):
    entity_description: ButtonEntityDescription

    def __init__(
        self,
        coordinator: PackageTrackerCoordinator,
        entry: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._suggested_object_id = description.key
        self._attr_icon = description.icon

    async def async_press(self) -> None:
        if self.entity_description.key == "sync":
            await self.coordinator.async_manual_sync()
            return
        if self.entity_description.key == "refresh_tracking":
            provider = self.coordinator.options.get(
                CONF_TRACKING_PROVIDER, TRACKING_PROVIDER_NONE
            )
            if provider == TRACKING_PROVIDER_NONE:
                raise HomeAssistantError(
                    "No external tracking provider is configured"
                )
            await self.coordinator.async_refresh_tracking_now()
            return
        raise HomeAssistantError("Unknown action")


BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="sync",
        translation_key="sync",
        icon="mdi:email-sync",
    ),
    ButtonEntityDescription(
        key="refresh_tracking",
        translation_key="refresh_tracking",
        icon="mdi:map-marker-path",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = get_runtime(hass, entry.entry_id)
    if runtime is None:
        return
    async_add_entities(
        PackageTrackerButton(runtime.coordinator, entry, description)
        for description in BUTTON_DESCRIPTIONS
    )
