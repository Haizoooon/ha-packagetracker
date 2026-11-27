"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_GMAIL_ACCOUNT,
    CONF_REDIRECT_URI,
    CONF_TOKEN,
    DOMAIN,
)
from custom_components.package_tracker.email_parser import EmailMessage

pytest_plugins = "pytest_homeassistant_custom_component"

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


def load_email_fixtures() -> dict[str, dict[str, Any]]:
    data = json.loads((FIXTURES / "emails.json").read_text(encoding="utf-8"))
    return {item["key"]: item for item in data}


def email_from_fixture(item: dict[str, Any]) -> EmailMessage:
    return EmailMessage(
        id=f"gmail-{item['key']}",
        thread_id=f"thread-{item['key']}",
        received_at=datetime.fromisoformat(item["received_at"]).astimezone(
            UTC
        ),
        sender_name=item["sender_name"],
        sender_email=item["sender_email"],
        subject=item["subject"],
        text=item.get("text", ""),
        html=item.get("html", ""),
        snippet=item.get("text", "")[:120],
    )


def make_config_entry(hass: HomeAssistant, **options: Any):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    defaults = {
        "sync_interval": 5,
        "initial_sync_days": 30,
        "gmail_query": "",
        "max_messages_per_sync": 1000,
        "store_email_subjects": True,
        "retention_days": 0,
        "notify_service": "",
        "notify_events": [],
        "tracking_provider": "none",
        "tracking_interval": 0,
    }
    defaults.update(options)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Package Tracker (test@example.com)",
        version=1,
        unique_id="test@example.com",
        data={
            CONF_CLIENT_ID: "123.apps.googleusercontent.com",
            CONF_CLIENT_SECRET: "secret",
            CONF_REDIRECT_URI: "https://example.com/auth/external/callback",
            CONF_TOKEN: {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_at": 9999999999,
                "token_type": "Bearer",
            },
            CONF_GMAIL_ACCOUNT: "test@example.com",
        },
        options=defaults,
    )
    entry.add_to_hass(hass)
    return entry
