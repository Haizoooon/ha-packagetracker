"""Tests for the Lovelace card websocket API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.const import DOMAIN
from custom_components.package_tracker.gmail_client import FetchResult

from .conftest import email_from_fixture, load_email_fixtures, make_config_entry

FIXTURES = load_email_fixtures()
MESSAGES = [
    email_from_fixture(FIXTURES[key])
    for key in ("amazon_order", "amazon_shipping", "dhl_delivered")
]
MESSAGES.sort(key=lambda message: message.received_at)


@pytest.fixture
def ws_entry(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-26 18:00:00+00:00")
    entry = make_config_entry(hass)
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        yield entry, fetch


@pytest.mark.asyncio
async def test_websocket_packages_and_detail(hass: HomeAssistant, ws_entry, hass_ws_client) -> None:
    entry, _fetch = ws_entry
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "package_tracker/packages"})
    response = await client.receive_json()
    assert response["success"] is True
    result = response["result"]
    assert result["version"] == "1.0.0"
    assert len(result["packages"]) == 1
    assert result["stats"]["total"] == 1
    assert result["stats"]["delivered_today"] == 1
    package = result["packages"][0]
    assert package["merchant"] == "Amazon"
    assert package["status"] == "delivered"
    assert package["config_entry_id"] == entry.entry_id

    await client.send_json(
        {
            "id": 2,
            "type": "package_tracker/package",
            "package_id": package["id"],
        }
    )
    response = await client.receive_json()
    assert response["success"] is True
    assert response["result"]["id"] == package["id"]
    assert response["result"]["status_history"]

    await client.send_json(
        {"id": 3, "type": "package_tracker/package", "package_id": "missing"}
    )
    response = await client.receive_json()
    assert response["success"] is False
    assert response["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_websocket_subscription(hass: HomeAssistant, ws_entry, hass_ws_client) -> None:
    entry, _fetch = ws_entry
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 4, "type": "package_tracker/subscribe"})
    response = await client.receive_json()
    assert response["success"] is True

    package_state = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    )
    package_id = package_state.attributes["package_id"]
    await hass.services.async_call(
        DOMAIN,
        "mark_completed",
        {"package_id": package_id, "completed": True},
        blocking=True,
    )
    event = await client.receive_json()
    assert event["type"] == "event"
    assert "packages" in event["event"]
