"""Tests for events and notification delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.const import (
    DOMAIN,
)
from custom_components.package_tracker.gmail_client import FetchResult

from .conftest import email_from_fixture, load_email_fixtures, make_config_entry

FIXTURES = load_email_fixtures()
MESSAGES = [
    email_from_fixture(FIXTURES[key])
    for key in (
        "amazon_order",
        "amazon_shipping",
        "dhl_out_for_delivery",
        "dhl_delivered",
    )
]
MESSAGES.sort(key=lambda message: message.received_at)


@pytest.fixture
def notify_calls():
    calls: list[dict] = []

    async def handler(call):
        calls.append(dict(call.data))

    return calls, handler


async def setup_notification_entry(hass, calls, handler, **options):
    hass.services.async_register("notify", "test", handler)
    entry = make_config_entry(
        hass,
        notify_service="test",
        notify_events=["delivered"],
        **options,
    )
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry, fetch


@pytest.mark.asyncio
async def test_delivered_notification_sent_once(
    hass: HomeAssistant, freezer, notify_calls
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    calls, handler = notify_calls
    _entry, fetch = await setup_notification_entry(hass, calls, handler)

    assert len(calls) == 1
    assert "delivered" in calls[0]["message"]
    assert "Logitech MX Master 4" in calls[0]["message"]
    assert calls[0]["title"] == "Parcel delivered"

    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        await hass.services.async_call(DOMAIN, "sync", {}, blocking=True)
        await hass.async_block_till_done()
    # Same e-mail must not notify again.
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_out_for_delivery_notification_uses_change_status(
    hass: HomeAssistant, freezer, notify_calls
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    calls, handler = notify_calls
    hass.services.async_register("notify", "test", handler)
    entry = make_config_entry(
        hass,
        notify_service="test",
        notify_events=["out_for_delivery"],
    )
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0]["title"] == "Parcel out for delivery"
    assert "14:00–18:00 Uhr" in calls[0]["message"]


@pytest.mark.asyncio
async def test_no_notification_without_service(
    hass: HomeAssistant, freezer, notify_calls
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    calls, handler = notify_calls
    hass.services.async_register("notify", "test", handler)
    entry = make_config_entry(hass, notify_service="", notify_events=["delivered"])
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert calls == []


@pytest.mark.asyncio
async def test_notifications_are_translated_to_german(
    hass: HomeAssistant, freezer, notify_calls
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    hass.config.language = "de"
    calls, handler = notify_calls
    hass.services.async_register("notify", "test", handler)
    entry = make_config_entry(
        hass,
        notify_service="test",
        notify_events=["delivered"],
    )
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0]["title"] == "Paket zugestellt"
    assert "zugestellt" in calls[0]["message"]


@pytest.mark.asyncio
async def test_mobile_app_notification_includes_tracking_url(
    hass: HomeAssistant, freezer, notify_calls
) -> None:
    freezer.move_to("2026-11-26 18:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    calls, handler = notify_calls
    hass.services.async_register("notify", "mobile_app_test", handler)
    entry = make_config_entry(
        hass,
        notify_service="mobile_app_test",
        notify_events=["delivered"],
    )
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0]["data"]["tag"].startswith("package_tracker_")
    assert "dhl.de" in calls[0]["data"]["url"]
