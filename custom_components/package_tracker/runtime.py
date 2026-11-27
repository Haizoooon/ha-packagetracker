"""Runtime objects shared by platforms, services and the websocket API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import PackageTrackerCoordinator
    from .gmail_client import GmailClient
    from .oauth import GoogleOAuth2Implementation
    from .package_manager import PackageManager
    from .storage import PackageTrackerStore


@dataclass(slots=True)
class EntryRuntime:
    entry: ConfigEntry
    coordinator: PackageTrackerCoordinator
    manager: PackageManager
    gmail: GmailClient
    implementation: GoogleOAuth2Implementation
    store: PackageTrackerStore


def get_runtimes(hass: HomeAssistant) -> dict[str, EntryRuntime]:
    data = hass.data.get(DOMAIN)
    if not isinstance(data, dict):
        return {}
    return {
        key: value
        for key, value in data.items()
        if isinstance(value, EntryRuntime)
    }


def get_runtime(hass: HomeAssistant, entry_id: str) -> EntryRuntime | None:
    return get_runtimes(hass).get(entry_id)


def get_primary_runtime(hass: HomeAssistant) -> EntryRuntime | None:
    runtimes = get_runtimes(hass)
    if not runtimes:
        return None
    return next(iter(runtimes.values()))
