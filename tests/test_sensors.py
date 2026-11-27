"""Integration tests for entities, services, events and persistence."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.const import (
    DOMAIN,
    EVENT_PACKAGE_DELIVERED,
    EVENT_PACKAGE_FOUND,
    EVENT_PACKAGE_UPDATED,
)
from custom_components.package_tracker.gmail_client import FetchResult

from .conftest import email_from_fixture, load_email_fixtures, make_config_entry

FIXTURES = load_email_fixtures()
KEYS = [
    "amazon_order",
    "amazon_shipping",
    "dhl_out_for_delivery",
    "dhl_delivered",
    "hermes_delay",
    "dpd_shipping",
    "dpd_pickup",
    "ups_shipped",
    "amazon_logistics",
    "return_label",
    "gls_return",
    "marketing",
]


def all_messages():
    messages = [
        email_from_fixture(FIXTURES[key])
        for key in KEYS
        if key not in {"return_label"}
    ]
    messages.sort(key=lambda message: message.received_at)
    return messages


@pytest.fixture
def gmail_fetch():
    fetch = AsyncMock(
        return_value=FetchResult(messages=all_messages(), query="test")
    )
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        yield fetch


async def setup_entry(
    hass: HomeAssistant,
    *,
    options: dict | None = None,
):
    entry = make_config_entry(hass, **(options or {}))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.asyncio
async def test_sensors_and_package_entities(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)

    assert hass.states.get("sensor.package_tracker_packages").state == "4"
    assert hass.states.get("sensor.package_tracker_deliveries_today").state == "1"
    assert hass.states.get("sensor.package_tracker_delivered_today").state == "1"
    assert hass.states.get("sensor.package_tracker_packages_in_transit").state == "3"
    assert hass.states.get("sensor.package_tracker_delayed").state == "1"
    next_delivery = hass.states.get("sensor.package_tracker_next_delivery")
    assert next_delivery.state == "2026-11-26"

    main = hass.states.get("sensor.package_tracker_packages")
    attrs = main.attributes
    assert attrs["counts"]["active"] == 4
    assert attrs["gmail"]["connected"] is True
    assert len(attrs["packages"]) == 6

    package_states = [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    ]
    assert len(package_states) == 6
    statuses = {state.state for state in package_states}
    assert "delivered" in statuses
    assert "out_for_delivery" in statuses
    assert "ready_for_pickup" in statuses
    assert "delayed" in statuses

    delivered = next(state for state in package_states if state.state == "delivered")
    assert delivered.attributes["tracking_number"] == "00340434161094000000"
    assert delivered.attributes["order"] is not None
    assert delivered.attributes["status_history"]

    assert hass.states.get("binary_sensor.package_tracker_delivery_today").state == "on"
    assert (
        hass.states.get("binary_sensor.package_tracker_package_out_for_delivery").state
        == "on"
    )
    assert hass.states.get("binary_sensor.package_tracker_delayed").state == "on"
    assert hass.states.get("binary_sensor.package_tracker_gmail_connected").state == "on"
    assert hass.states.get("button.package_tracker_sync").state != "unavailable"
    assert (
        hass.states.get("button.package_tracker_refresh_tracking").state
        != "unavailable"
    )


@pytest.mark.asyncio
async def test_events_are_fired(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    found: list = []
    delivered: list = []
    updated: list = []

    unsub_found = hass.bus.async_listen(
        EVENT_PACKAGE_FOUND, lambda event: found.append(event)
    )
    unsub_delivered = hass.bus.async_listen(
        EVENT_PACKAGE_DELIVERED, lambda event: delivered.append(event)
    )
    unsub_updated = hass.bus.async_listen(
        EVENT_PACKAGE_UPDATED, lambda event: updated.append(event)
    )
    try:
        await setup_entry(hass)
        await hass.async_block_till_done()
    finally:
        unsub_found()
        unsub_delivered()
        unsub_updated()

    assert len(found) == 6
    assert len(delivered) == 1
    event = delivered[0]
    assert event.data["merchant"] == "Amazon"
    assert event.data["status"] == "delivered"
    assert event.data["carrier"] == "dhl"
    assert event.data["tracking_number"] == "00340434161094000000"
    assert event.data["tracking_url"]
    assert event.data["product_name"]
    assert updated


@pytest.mark.asyncio
async def test_manual_delivered_service(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    package_states = [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
        and state.state == "out_for_delivery"
    ]
    assert package_states
    package_id = package_states[0].attributes["package_id"]

    response = await hass.services.async_call(
        DOMAIN,
        "mark_delivered",
        {"package_id": package_id, "delivered_at": "2026-11-26"},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()
    assert response["ok"] is True
    assert response["status"] == "delivered"
    sensor = hass.states.get(package_states[0].entity_id)
    assert sensor.state == "delivered"

    packages = await hass.services.async_call(
        DOMAIN,
        "get_packages",
        {"status": "delivered"},
        blocking=True,
        return_response=True,
    )
    assert packages["count"] == 2


@pytest.mark.asyncio
async def test_completed_and_deleted_services(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    package_states = [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    ]
    package_id = package_states[0].attributes["package_id"]

    await hass.services.async_call(
        DOMAIN,
        "mark_completed",
        {"package_id": package_id, "completed": True},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "delete_package",
        {"package_id": package_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert not any(
        state.attributes.get("package_id") == package_id
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    )


@pytest.mark.asyncio
async def test_data_persists_across_reload(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    entry = await setup_entry(hass)
    first_state = hass.states.get("sensor.package_tracker_packages").state
    first_ids = {
        state.attributes.get("package_id")
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    }
    assert first_state == "4"
    assert len(first_ids) == 6

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED

    await setup_entry(hass)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.package_tracker_packages").state == first_state
    second_ids = {
        state.attributes.get("package_id")
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    }
    assert second_ids == first_ids


@pytest.mark.asyncio
async def test_manual_sync_does_not_duplicate(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    calls_before = gmail_fetch.await_count
    response = await hass.services.async_call(
        DOMAIN, "sync", {}, blocking=True, return_response=True
    )
    await hass.async_block_till_done()
    assert response["ok"] is True
    assert gmail_fetch.await_count == calls_before + 1
    assert hass.states.get("sensor.package_tracker_packages").state == "4"


@pytest.mark.asyncio
async def test_update_package_service(hass: HomeAssistant, freezer, gmail_fetch) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    package_states = [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    ]
    package_id = package_states[0].attributes["package_id"]
    response = await hass.services.async_call(
        DOMAIN,
        "update_package",
        {
            "package_id": package_id,
            "merchant": "Testhändler",
            "carrier": "DHL",
            "expected_delivery": "2026-12-01",
            "delivery_window": "09:00–12:00 Uhr",
            "status": "delayed",
        },
        blocking=True,
        return_response=True,
    )
    assert response["ok"] is True
    state = next(
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("package_id") == package_id
    )
    assert state.attributes["merchant"] == "Testhändler"
    assert state.attributes["carrier"] == "dhl"
    assert state.attributes["expected_delivery"] == "2026-12-01"
    assert state.state == "delayed"


@pytest.mark.asyncio
async def test_delete_all_data_requires_confirmation(
    hass: HomeAssistant, freezer, gmail_fetch
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "delete_all_data", {"confirm": False}, blocking=True
        )
    assert hass.states.get("sensor.package_tracker_packages").state == "4"

    await hass.services.async_call(
        DOMAIN, "delete_all_data", {"confirm": True}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.package_tracker_packages").state == "0"
    assert not [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    ]


@pytest.mark.asyncio
async def test_refresh_tracking_button_requires_provider(
    hass: HomeAssistant, freezer, gmail_fetch
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.package_tracker_refresh_tracking"},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_refresh_service_publishes_snapshot(
    hass: HomeAssistant, freezer, gmail_fetch
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    await setup_entry(hass)
    response = await hass.services.async_call(
        DOMAIN, "refresh", {}, blocking=True, return_response=True
    )
    assert response == {"ok": True, "entries": 1}
    assert hass.states.get("sensor.package_tracker_packages").state == "4"
