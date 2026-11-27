"""Persistent storage for Package Tracker.

Uses Home Assistant's Store helper (atomic JSON in ``.storage``).  The manager
is the only producer of the stored document.  Saving is debounced during
syncs and flushed on unload.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class LoadResult:
    data: dict[str, Any] | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.data is not None and self.error is None


class PackageTrackerStore:
    """Versioned Store wrapper for one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{entry_id}",
            private=True,
            atomic_writes=True,
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._hass = hass

    async def async_load(self) -> LoadResult:
        try:
            raw = await self._store.async_load()
        except (ValueError, OSError, UnicodeDecodeError) as err:
            # Store handles JSON corruption itself; this covers unexpected
            # value errors from a partial/malformed envelope.
            _LOGGER.error("Package Tracker storage is corrupt: %s", type(err).__name__)
            return LoadResult(None, "corrupt")
        except Exception as err:
            _LOGGER.exception("Unexpected storage error: %s", type(err).__name__)
            return LoadResult(None, "unexpected")

        if not raw:
            return LoadResult(None)
        if not isinstance(raw, dict):
            return LoadResult(None, "invalid")
        version = raw.get("version")
        if version not in (None, STORAGE_VERSION):
            _LOGGER.warning(
                "Unsupported Package Tracker storage version %s; starting empty",
                version,
            )
            return LoadResult(None, "version")
        data = raw.get("data")
        if data is None:
            data = raw
        if not isinstance(data, dict):
            return LoadResult(None, "invalid")
        return LoadResult(data)

    def async_schedule_save(self, data_func: Callable[[], dict[str, Any]]) -> None:
        self._store.async_delay_save(data_func, STORAGE_SAVE_DELAY)

    async def async_save(self, data: dict[str, Any]) -> None:
        await self._store.async_save(data)

    async def async_delete(self) -> None:
        try:
            await self._store.async_remove()
        except OSError as err:
            _LOGGER.warning("Could not remove Package Tracker storage: %s", err)


def store_diagnostics() -> dict[str, str]:
    return {"domain": DOMAIN, "storage_key": STORAGE_KEY}
