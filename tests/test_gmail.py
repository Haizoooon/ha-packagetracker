"""Tests for Gmail REST client, MIME decoding and OAuth probing."""

from __future__ import annotations

import base64
from datetime import UTC, datetime

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.gmail_client import (
    GmailAuthError,
    GmailClient,
    GmailConnectionError,
    GmailQueryError,
    GmailRateLimitError,
    GmailScopeError,
    async_probe_account,
    gmail_message_to_email,
)


def b64(value: str, encoding: str = "utf-8") -> str:
    return (
        base64.urlsafe_b64encode(value.encode(encoding))
        .decode("ascii")
        .rstrip("=")
    )


def raw_message(
    message_id: str = "m1",
    *,
    subject: str = "Ihr Paket wurde versendet",
    text: str = "Sendungsnummer: 00340434161094000000",
    html: str = "<html><body>versendet</body></html>",
    received_at: str = "2026-11-22T10:30:00+00:00",
) -> dict:
    internal = int(datetime.fromisoformat(received_at).timestamp() * 1000)
    return {
        "id": message_id,
        "threadId": "t1",
        "internalDate": str(internal),
        "snippet": text[:80],
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "=?UTF-8?Q?Amazon.de?= <versand@amazon.de>"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Sun, 22 Nov 2026 10:30:00 +0000"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "Content-Type", "value": 'text/plain; charset="utf-8"'}
                    ],
                    "body": {"data": b64(text)},
                },
                {
                    "mimeType": "text/html",
                    "headers": [
                        {"name": "Content-Type", "value": 'text/html; charset="utf-8"'}
                    ],
                    "body": {"data": b64(html)},
                },
            ],
        },
    }


def test_mime_decoding_and_headers() -> None:
    message = gmail_message_to_email(raw_message())
    assert message is not None
    assert message.id == "m1"
    assert message.thread_id == "t1"
    assert message.sender_name == "Amazon.de"
    assert message.sender_email == "versand@amazon.de"
    assert message.subject == "Ihr Paket wurde versendet"
    assert "00340434161094000000" in message.text
    assert "versendet" in message.html
    assert message.received_at == datetime(2026, 11, 22, 10, 30, tzinfo=UTC)


def test_mime_decoding_nested_and_iso_charset() -> None:
    raw = {
        "id": "m2",
        "threadId": "t2",
        "internalDate": "1763807400000",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "DHL <noreply@dhl.de>"},
                {"name": "Subject", "value": "Sendung unterwegs"},
            ],
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "headers": [
                                {
                                    "name": "Content-Type",
                                    "value": "text/plain; charset=iso-8859-1",
                                }
                            ],
                            "body": {
                                "data": b64("Grüße von DHL", encoding="iso-8859-1")
                            },
                        }
                    ],
                }
            ],
        },
    }
    message = gmail_message_to_email(raw)
    assert message is not None
    assert message.text == "Grüße von DHL"
    assert message.html == ""
    assert message.sender_email == "noreply@dhl.de"


def test_mime_decoding_invalid_input() -> None:
    assert gmail_message_to_email({}) is None
    message = gmail_message_to_email(
        {
            "id": "bad",
            "internalDate": "not-a-number",
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": "!!!not-base64!!!"},
            },
        }
    )
    assert message is not None
    assert message.text == ""
    assert message.received_at is not None


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None, headers=None):
        self.status = status
        self._payload = payload or {}
        self.headers = headers or {}

    async def json(self, content_type=None):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def async_request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses(url, kwargs)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_fetch_messages_paginates_and_sorts(hass: HomeAssistant) -> None:
    messages = {
        "a": raw_message("a", received_at="2026-11-22T10:00:00+00:00"),
        "b": raw_message("b", received_at="2026-11-21T10:00:00+00:00"),
        "c": raw_message("c", received_at="2026-11-23T10:00:00+00:00"),
    }
    pages = {
        None: {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"},
        "p2": {"messages": [{"id": "b"}, {"id": "c"}]},
    }

    def responder(url, kwargs):
        if url.endswith("/messages"):
            return FakeResponse(200, pages[kwargs["params"].get("pageToken")])
        message_id = url.rsplit("/", 1)[-1]
        return FakeResponse(200, messages[message_id])

    session = FakeSession(responder)
    client = GmailClient(hass, session)  # type: ignore[arg-type]
    result = await client.async_fetch_messages(
        last_sync=None, base_query="from:amazon", initial_days=30
    )

    assert [message.id for message in result.messages] == ["b", "a", "c"]
    assert result.truncated is False
    list_call = next(call for call in session.calls if call[1].endswith("/messages"))
    assert "newer_than:30d" in list_call[2]["params"]["q"]
    assert "from:amazon" in list_call[2]["params"]["q"]


@pytest.mark.asyncio
async def test_fetch_messages_incremental_query(hass: HomeAssistant) -> None:
    def responder(url, kwargs):
        if url.endswith("/messages"):
            return FakeResponse(200, {"messages": []})
        return FakeResponse(404, {})

    session = FakeSession(responder)
    client = GmailClient(hass, session)  # type: ignore[arg-type]
    last_sync = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    await client.async_fetch_messages(last_sync=last_sync, base_query="")
    list_call = next(call for call in session.calls if call[1].endswith("/messages"))
    assert "after:" in list_call[2]["params"]["q"]
    assert "newer_than" not in list_call[2]["params"]["q"]


@pytest.mark.asyncio
async def test_error_mapping(hass: HomeAssistant) -> None:
    cases = [
        (401, {}, GmailAuthError),
        (403, {"error": {"errors": [{"reason": "insufficientPermissions"}]}}, GmailScopeError),
        (403, {"error": {"errors": [{"reason": "rateLimitExceeded"}]}}, GmailRateLimitError),
        (429, {}, GmailRateLimitError),
        (400, {"error": {"message": "Invalid query"}}, GmailQueryError),
        (500, {}, GmailConnectionError),
    ]
    for status, payload, expected in cases:
        session = FakeSession(lambda url, kwargs, s=status, p=payload: FakeResponse(s, p))
        client = GmailClient(hass, session)  # type: ignore[arg-type]
        with pytest.raises(expected):
            await client.async_get_profile()


@pytest.mark.asyncio
async def test_network_error_mapping(hass: HomeAssistant) -> None:
    from aiohttp import ClientConnectionError

    session = FakeSession(lambda url, kwargs: ClientConnectionError("boom"))
    client = GmailClient(hass, session)  # type: ignore[arg-type]
    with pytest.raises(GmailConnectionError):
        await client.async_get_profile()


@pytest.mark.asyncio
async def test_profile_is_cached(hass: HomeAssistant) -> None:
    def responder(url, kwargs):
        return FakeResponse(
            200,
            {
                "emailAddress": "test@example.com",
                "messagesTotal": 12,
                "threadsTotal": 4,
                "historyId": "1",
            },
        )

    session = FakeSession(responder)
    client = GmailClient(hass, session)  # type: ignore[arg-type]
    assert (await client.async_get_profile())["emailAddress"] == "test@example.com"
    assert (await client.async_get_profile())["emailAddress"] == "test@example.com"
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_probe_account(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        json={"emailAddress": "probe@example.com"},
    )
    profile = await async_probe_account(
        hass, {"access_token": "token", "token_type": "Bearer"}
    )
    assert profile["emailAddress"] == "probe@example.com"
    assert len(aioclient_mock.mock_calls) == 1


@pytest.mark.asyncio
async def test_probe_account_scope_error(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        status=403,
        json={"error": {"errors": [{"reason": "insufficientPermissions"}]}},
    )
    with pytest.raises(GmailScopeError):
        await async_probe_account(hass, {"access_token": "token"})
