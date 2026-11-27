"""Tests for OAuth config flow, reauth and options."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.package_tracker import config_flow as config_flow_module
from custom_components.package_tracker.const import DOMAIN
from custom_components.package_tracker.gmail_client import FetchResult
from custom_components.package_tracker.oauth import GoogleOAuth2Implementation

from .conftest import make_config_entry

TOKEN = {
    "access_token": "new-access",
    "refresh_token": "new-refresh",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
}
PROFILE = {"emailAddress": "flow@example.com"}


@pytest.fixture
def flow_mocks(monkeypatch):
    monkeypatch.setattr(
        config_flow_module,
        "resolve_redirect_uri",
        lambda hass: "https://example.com/auth/external/callback",
    )
    monkeypatch.setattr(
        GoogleOAuth2Implementation,
        "async_resolve_external_data",
        AsyncMock(return_value=dict(TOKEN)),
    )
    monkeypatch.setattr(
        config_flow_module, "async_probe_account", AsyncMock(return_value=dict(PROFILE))
    )
    fetch = AsyncMock(return_value=FetchResult(messages=[], query="test"))
    monkeypatch.setattr(
        "custom_components.package_tracker.gmail_client.GmailClient.async_fetch_messages",
        fetch,
    )
    return fetch


@pytest.mark.asyncio
async def test_full_config_flow(hass: HomeAssistant, flow_mocks) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "client_id": "123456.apps.googleusercontent.com",
            "client_secret": "secret",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.EXTERNAL_STEP
    assert "accounts.google.com" in result["url"]
    assert "gmail.readonly" in result["url"]
    assert "access_type=offline" in result["url"] or "access_type%3Doffline" in result["url"]

    flow_id = result["flow_id"]
    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            "code": "auth-code",
            "state": {
                "flow_id": flow_id,
                "redirect_uri": "https://example.com/auth/external/callback",
            },
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.EXTERNAL_STEP_DONE

    result = await hass.config_entries.flow.async_configure(flow_id, {})
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            "sync_interval": 10,
            "initial_sync_days": 14,
            "notify_service": "",
            "notify_events": [],
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.data["gmail_account"] == "flow@example.com"
    assert entry.data["token"]["refresh_token"] == "new-refresh"
    assert entry.options["sync_interval"] == 10
    assert entry.options["initial_sync_days"] == 14
    assert entry.unique_id == "flow@example.com"


@pytest.mark.asyncio
async def test_config_flow_requires_https_redirect(hass: HomeAssistant, monkeypatch) -> None:
    monkeypatch.setattr(
        config_flow_module,
        "resolve_redirect_uri",
        lambda hass: (_ for _ in ()).throw(config_flow_module.NoRedirectUriError()),
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "client_id": "123456.apps.googleusercontent.com",
            "client_secret": "secret",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "no_url_available"


@pytest.mark.asyncio
async def test_config_flow_invalid_client_id(hass: HomeAssistant, flow_mocks) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"client_id": "not-google", "client_secret": "secret"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_client_id"


@pytest.mark.asyncio
async def test_options_flow_updates_settings(hass: HomeAssistant) -> None:
    entry = make_config_entry(hass, sync_interval=5)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "sync_interval": 15,
            "initial_sync_days": 60,
            "gmail_query": "(from:amazon)",
            "max_messages_per_sync": 500,
            "store_email_subjects": False,
            "retention_days": 30,
            "notify_service": "mobile_app_test",
            "notify_events": ["delivered", "delayed"],
            "tracking_provider": "none",
            "tracking_interval": 0,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["sync_interval"] == 15
    assert entry.options["initial_sync_days"] == 60
    assert entry.options["store_email_subjects"] is False
    assert entry.options["retention_days"] == 30
    assert entry.options["notify_events"] == ["delivered", "delayed"]


@pytest.mark.asyncio
async def test_options_flow_requires_dhl_key(hass: HomeAssistant) -> None:
    entry = make_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "sync_interval": 5,
            "initial_sync_days": 30,
            "gmail_query": "",
            "max_messages_per_sync": 1000,
            "store_email_subjects": True,
            "retention_days": 90,
            "notify_service": "",
            "notify_events": [],
            "tracking_provider": "dhl_unified",
            "tracking_api_key": "",
            "tracking_interval": 60,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "tracking_api_key_required"


@pytest.mark.asyncio
async def test_reauth_updates_token(hass: HomeAssistant, flow_mocks, monkeypatch) -> None:
    entry = make_config_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    monkeypatch.setattr(
        config_flow_module,
        "async_probe_account",
        AsyncMock(return_value={"emailAddress": "test@example.com"}),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is data_entry_flow.FlowResultType.EXTERNAL_STEP
    flow_id = result["flow_id"]

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            "code": "new-code",
            "state": {
                "flow_id": flow_id,
                "redirect_uri": "https://example.com/auth/external/callback",
            },
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.EXTERNAL_STEP_DONE

    result = await hass.config_entries.flow.async_configure(flow_id, {})
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["token"]["access_token"] == "new-access"
    assert entry.data["token"]["refresh_token"] == "new-refresh"
