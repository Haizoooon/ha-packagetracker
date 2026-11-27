"""Tests for the persistent Store wrapper."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.package_manager import PackageManager
from custom_components.package_tracker.storage import PackageTrackerStore

from .test_package_manager import manager, parsed


@pytest.mark.asyncio
async def test_save_and_load_roundtrip(hass: HomeAssistant) -> None:
    store = PackageTrackerStore(hass, "entry-1")
    assert (await store.async_load()).data is None

    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    mgr.last_sync = "2026-11-26T12:00:00+00:00"
    await store.async_save(mgr.to_dict())

    loaded = await store.async_load()
    assert loaded.ok
    assert loaded.data is not None
    restored = PackageManager.from_dict(loaded.data)
    assert len(restored.shipments) == 1
    assert len(restored.orders) == 1
    assert restored.last_sync == "2026-11-26T12:00:00+00:00"
    assert restored.processed_emails


@pytest.mark.asyncio
async def test_corrupt_storage_is_moved_aside(
    hass: HomeAssistant, monkeypatch
) -> None:
    store = PackageTrackerStore(hass, "entry-corrupt")

    async def _raise():
        raise ValueError("broken envelope")

    monkeypatch.setattr(store._store, "_async_load", _raise)

    loaded = await store.async_load()
    assert loaded.data is None
    assert loaded.error == "corrupt"


@pytest.mark.asyncio
async def test_delete_removes_storage(hass: HomeAssistant) -> None:
    store = PackageTrackerStore(hass, "entry-delete")
    await store.async_save({"shipments": [], "orders": []})
    await store.async_delete()
    store._store._manager.async_invalidate(store._store.key)
    assert (await store.async_load()).data is None
