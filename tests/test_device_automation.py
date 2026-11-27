"""Tests for diagnostics, device automations and repairs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.package_tracker import (
    device_action,
    device_condition,
    device_trigger,
)
from custom_components.package_tracker.const import (
    DOMAIN,
    EVENT_PACKAGE_DELIVERED,
)
from custom_components.package_tracker.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.package_tracker.gmail_client import FetchResult

from .conftest import email_from_fixture, load_email_fixtures, make_config_entry

FIXTURES = load_email_fixtures()
MESSAGES = [
    email_from_fixture(FIXTURES[key])
    for key in ("amazon_order", "amazon_shipping", "dhl_delivered")
]
MESSAGES.sort(key=lambda message: message.received_at)


@pytest.fixture
def configured_entry(hass: HomeAssistant, freezer):
    freezer.move_to("2026-11-26 18:00:00+00:00")
    entry = make_config_entry(hass)
    fetch = AsyncMock(return_value=FetchResult(messages=MESSAGES, query="test"))
    with patch(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        new=fetch,
    ):
        yield entry, fetch


async def _setup(hass, entry) -> str:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    return device.id


@pytest.mark.asyncio
async def test_diagnostics_redacts_secrets(
    hass: HomeAssistant, configured_entry
) -> None:
    entry, _ = configured_entry
    await _setup(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["domain"] == DOMAIN
    assert diagnostics["entry"]["data"]["token"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["client_secret"] == "**REDACTED**"
    assert diagnostics["gmail"]["account"] == "t***@example.com"
    assert diagnostics["storage"]["packages"] == 1
    assert diagnostics["packages"][0]["tracking_number"] != "00340434161094000000"
    assert "tracking_url" not in diagnostics["packages"][0]
    assert "emails" not in diagnostics["packages"][0]


@pytest.mark.asyncio
async def test_device_triggers_conditions_actions(
    hass: HomeAssistant, configured_entry
) -> None:
    entry, _ = configured_entry
    device_id = await _setup(hass, entry)

    triggers = await device_trigger.async_get_triggers(hass, device_id)
    assert {trigger["type"] for trigger in triggers} >= {
        "package_delivered",
        "package_status_changed",
        "package_delayed",
    }
    capabilities = await device_trigger.async_get_trigger_capabilities(
        hass, {"type": "package_delivered"}
    )
    assert capabilities["extra_fields"].schema

    calls: list[dict] = []

    def action(variables, context=None):
        calls.append(variables)

    trigger_config = {
        "platform": "device",
        "domain": DOMAIN,
        "device_id": device_id,
        "type": "package_delivered",
    }
    unsub = await device_trigger.async_attach_trigger(
        hass,
        trigger_config,
        action,
        {"trigger_data": {}, "variables": {}},
    )
    hass.bus.async_fire(EVENT_PACKAGE_DELIVERED, {"package_id": "pkg_test"})
    await hass.async_block_till_done()
    unsub()
    assert len(calls) == 1

    checker = device_condition.async_condition_from_config(
        hass,
        {"type": "carrier_is", "carrier": "dhl", "device_id": device_id},
    )
    assert checker(hass, {}) is True
    checker = device_condition.async_condition_from_config(
        hass,
        {"type": "merchant_is", "merchant": "Amazon", "device_id": device_id},
    )
    assert checker(hass, {}) is True
    checker = device_condition.async_condition_from_config(
        hass,
        {"type": "product_contains", "text": "MX Master", "device_id": device_id},
    )
    assert checker(hass, {}) is True

    actions = await device_action.async_get_actions(hass, device_id)
    assert {action["type"] for action in actions} >= {"sync", "mark_completed"}
    package_state = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.startswith("sensor.package_tracker_package_")
    )
    package_id = package_state.attributes["package_id"]
    await device_action.async_call_action_from_config(
        hass,
        {"type": "mark_completed", "package_id": package_id, "completed": True},
        {},
        None,
    )
    await hass.async_block_till_done()
    state = next(
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("package_id") == package_id
    )
    assert state.attributes["completed"] is True
