"""Async Gmail API client.

Uses the official REST API directly (no heavy Google SDK, no blocking
calls).  Authentication is handled by Home Assistant's OAuth2 session, which
also refreshes and stores access tokens.

Only ``gmail.readonly`` is requested.  Message bodies are decoded in memory,
handed to the parser and then discarded.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import (
    CONF_GMAIL_ACCOUNT,
    DEFAULT_GMAIL_QUERY,
    DEFAULT_INITIAL_SYNC_DAYS,
    DEFAULT_MAX_MESSAGES,
    GMAIL_API_BASE,
    MAX_BODY_CHARS,
)
from .email_parser import EmailMessage, parse_sender
from .util import clean_whitespace, html_to_text, truncate

_LOGGER = logging.getLogger(__name__)

_BASE64URL = re.compile(r"[^A-Za-z0-9+/=]")


class GmailError(Exception):
    """Base class for Gmail errors (safe to show to the user)."""


class GmailAuthError(GmailError):
    """Access token was rejected."""


class GmailScopeError(GmailError):
    """The readonly Gmail scope is missing or access was denied."""


class GmailRateLimitError(GmailError):
    """Gmail asked us to slow down."""


class GmailConnectionError(GmailError):
    """Network error while talking to Gmail."""


class GmailQueryError(GmailError):
    """The configured Gmail search query is invalid."""


@dataclass(slots=True)
class FetchResult:
    """Result of one Gmail sync."""

    messages: list[EmailMessage] = field(default_factory=list)
    query: str = ""
    truncated: bool = False
    listed: int = 0

    @property
    def newest(self) -> datetime | None:
        if not self.messages:
            return None
        return max(message.received_at for message in self.messages)

    @property
    def oldest(self) -> datetime | None:
        if not self.messages:
            return None
        return min(message.received_at for message in self.messages)


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return clean_whitespace(str(make_header(decode_header(value))))
    except (UnicodeDecodeError, LookupError, ValueError):
        return clean_whitespace(value)


def _decode_body(data: str, charset: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        try:
            raw = base64.b64decode(_BASE64URL.sub("", padded))
        except (ValueError, TypeError):
            return ""
    for encoding in (charset, "utf-8", "iso-8859-1"):
        if not encoding:
            continue
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def _part_charset(part: dict[str, Any]) -> str | None:
    charset = part.get("body", {}).get("charset") if isinstance(part.get("body"), dict) else None
    if charset:
        return str(charset)
    for header in part.get("headers", []) or []:
        name = str(header.get("name", "")).lower()
        value = str(header.get("value", ""))
        if name == "content-type":
            match = re.search(r"charset=\"?([^\";]+)\"?", value, re.IGNORECASE)
            if match:
                return match.group(1)
    return None


def _walk_parts(part: dict[str, Any], plain: list[str], html: list[str]) -> None:
    mime_type = str(part.get("mimeType", "")).lower()
    body = part.get("body", {})
    body_data = body.get("data") if isinstance(body, dict) else None
    filename = part.get("filename") or ""
    headers = {
        str(header.get("name", "")).lower(): str(header.get("value", ""))
        for header in part.get("headers", []) or []
    }
    disposition = headers.get("content-disposition", "").lower()

    if body_data and not filename and "attachment" not in disposition:
        if mime_type == "text/plain":
            plain.append(_decode_body(str(body_data), _part_charset(part)))
        elif mime_type == "text/html":
            html.append(_decode_body(str(body_data), _part_charset(part)))

    for child in part.get("parts", []) or []:
        if isinstance(child, dict):
            _walk_parts(child, plain, html)


def gmail_message_to_email(raw: dict[str, Any]) -> EmailMessage | None:
    """Convert a Gmail ``messages.get`` response into an EmailMessage."""
    message_id = str(raw.get("id") or "")
    if not message_id:
        return None
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
    headers = {
        str(header.get("name", "")).lower(): str(header.get("value", ""))
        for header in payload.get("headers", []) or []
    }

    sender_name, sender_email = parse_sender(
        _decode_header(headers.get("from", ""))
    )
    subject = _decode_header(headers.get("subject", ""))

    internal_ms = raw.get("internalDate")
    received_at: datetime | None = None
    if internal_ms is not None:
        try:
            received_at = datetime.fromtimestamp(int(internal_ms) / 1000, tz=UTC)
        except (ValueError, TypeError, OSError, OverflowError):
            received_at = None
    if received_at is None:
        date_header = headers.get("date")
        if date_header:
            try:
                parsed = parsedate_to_datetime(date_header)
                received_at = parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except (TypeError, ValueError, OverflowError):
                received_at = None
    if received_at is None:
        received_at = datetime.now(UTC)

    plain: list[str] = []
    html: list[str] = []
    _walk_parts(payload, plain, html)
    text = max(plain, key=len) if plain else ""
    html_text = max(html, key=len) if html else ""
    if not text and html_text:
        text = html_to_text(html_text)
    text = text[:MAX_BODY_CHARS]
    html_text = html_text[:MAX_BODY_CHARS]

    return EmailMessage(
        id=message_id,
        thread_id=str(raw.get("threadId")) if raw.get("threadId") else None,
        received_at=received_at,
        sender_name=sender_name,
        sender_email=sender_email,
        subject=truncate(subject, 400) or "",
        text=text,
        html=html_text,
        snippet=truncate(str(raw.get("snippet", "")), 300) or "",
    )


def _error_detail(response: Any, payload: dict[str, Any] | None) -> str:
    if payload:
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            errors = error.get("errors")
            if isinstance(errors, list) and errors:
                reason = errors[0].get("reason") if isinstance(errors[0], dict) else None
                return f"{reason or ''} {message or ''}".strip()[:300]
            if message:
                return str(message)[:300]
        if isinstance(error, str):
            return error[:300]
    return f"HTTP {response.status}"


class GmailClient:
    """Small, typed wrapper around the Gmail REST API."""

    def __init__(self, hass: HomeAssistant, session: OAuth2Session) -> None:
        self.hass = hass
        self._session = session
        self._profile: dict[str, Any] | None = None

    async def async_get_profile(self, *, force: bool = False) -> dict[str, Any]:
        if self._profile is not None and not force:
            return self._profile
        response = await self._async_request(
            "GET", f"{GMAIL_API_BASE}/users/me/profile"
        )
        data = await self._async_json(response)
        self._profile = {
            "emailAddress": data.get("emailAddress"),
            "messagesTotal": data.get("messagesTotal"),
            "threadsTotal": data.get("threadsTotal"),
            "historyId": data.get("historyId"),
        }
        return self._profile

    async def async_fetch_messages(
        self,
        *,
        last_sync: datetime | None,
        base_query: str | None = None,
        initial_days: int = DEFAULT_INITIAL_SYNC_DAYS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> FetchResult:
        """Fetch messages for one sync window."""
        initial_days = max(1, min(int(initial_days or DEFAULT_INITIAL_SYNC_DAYS), 365))
        max_messages = max(1, min(int(max_messages or DEFAULT_MAX_MESSAGES), 2000))
        query_parts: list[str] = []
        base = (base_query if base_query is not None else DEFAULT_GMAIL_QUERY).strip()
        if base:
            query_parts.append(f"({base})")
        if last_sync is None:
            query_parts.append(f"newer_than:{initial_days}d")
        else:
            # Gmail's after: operator has day granularity.  A three day
            # overlap plus the persistent processed-id set guarantees that no
            # archived or delayed mail is missed and nothing is processed
            # twice.
            after = int(last_sync.timestamp()) - 3 * 86400
            query_parts.append(f"after:{max(0, after)}")
        query_parts.append("-in:chats")
        query = " ".join(query_parts)

        listed, truncated = await self._async_list_messages(query, max_messages)

        messages: list[EmailMessage] = []
        # Sequential-ish fetching with a small concurrency limit keeps quota
        # usage predictable and preserves memory use.
        for start in range(0, len(listed), 5):
            batch = listed[start : start + 5]
            results = await self._async_gather_batch(batch)
            messages.extend(message for message in results if message is not None)

        messages.sort(key=lambda message: message.received_at)
        _LOGGER.debug(
            "Gmail sync query returned %s messages (%s decoded, truncated=%s)",
            len(listed),
            len(messages),
            truncated,
        )
        return FetchResult(
            messages=messages,
            query=query,
            truncated=truncated,
            listed=len(listed),
        )

    async def _async_gather_batch(
        self, message_ids: list[str]
    ) -> list[EmailMessage | None]:
        async def fetch(message_id: str) -> EmailMessage | None:
            try:
                return await self.async_get_message(message_id)
            except (GmailAuthError, GmailScopeError, GmailRateLimitError):
                raise
            except GmailError as err:
                _LOGGER.warning("Could not fetch one Gmail message: %s", err)
                return None

        return await asyncio.gather(*(fetch(message_id) for message_id in message_ids))

    async def async_get_message(self, message_id: str) -> EmailMessage | None:
        response = await self._async_request(
            "GET",
            f"{GMAIL_API_BASE}/users/me/messages/{quote(message_id)}",
            params={"format": "full"},
        )
        raw = await self._async_json(response)
        return gmail_message_to_email(raw)

    async def _async_list_messages(
        self, query: str, max_messages: int
    ) -> tuple[list[str], bool]:
        result: list[str] = []
        page_token: str | None = None
        while len(result) < max_messages:
            params: dict[str, Any] = {
                "q": query,
                "maxResults": min(100, max_messages - len(result)),
                "fields": "messages/id,nextPageToken,resultSizeEstimate",
            }
            if page_token:
                params["pageToken"] = page_token
            response = await self._async_request(
                "GET", f"{GMAIL_API_BASE}/users/me/messages", params=params
            )
            data = await self._async_json(response)
            for message in data.get("messages", []) or []:
                message_id = message.get("id") if isinstance(message, dict) else None
                if message_id and message_id not in result:
                    result.append(str(message_id))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        truncated = len(result) >= max_messages and bool(page_token)
        if len(result) > max_messages:
            result = result[:max_messages]
        return result, truncated

    async def _async_request(self, method: str, url: str, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", 30)
        try:
            response = await self._session.async_request(method, url, **kwargs)
        except ConfigEntryAuthFailed:
            raise
        except (ClientError, TimeoutError) as err:
            raise GmailConnectionError(
                f"Gmail is unreachable ({type(err).__name__})"
            ) from err

        if response.status == HTTPStatus.UNAUTHORIZED:
            raise GmailAuthError("Gmail denied access")
        if response.status == HTTPStatus.FORBIDDEN:
            payload = await self._safe_json(response)
            detail = _error_detail(response, payload)
            lower = detail.casefold()
            if "rate" in lower or "quota" in lower:
                raise GmailRateLimitError(detail)
            if "insufficient" in lower or "scope" in lower or "permission" in lower:
                raise GmailScopeError(detail)
            raise GmailAuthError(detail)
        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = response.headers.get("Retry-After")
            raise GmailRateLimitError(
                f"Gmail rate limit reached (Retry-After: {retry_after or 'unknown'})"
            )
        if response.status == HTTPStatus.BAD_REQUEST:
            payload = await self._safe_json(response)
            raise GmailQueryError(_error_detail(response, payload))
        if response.status >= 500:
            raise GmailConnectionError(f"Gmail server error (HTTP {response.status})")
        if response.status >= 400:
            payload = await self._safe_json(response)
            raise GmailError(_error_detail(response, payload))
        return response

    @staticmethod
    async def _async_json(response: Any) -> dict[str, Any]:
        try:
            data = await response.json(content_type=None)
        except (ValueError, TypeError) as err:
            raise GmailError("Invalid Gmail response") from err
        return data if isinstance(data, dict) else {}

    @staticmethod
    async def _safe_json(response: Any) -> dict[str, Any] | None:
        try:
            data = await response.json(content_type=None)
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None


async def async_probe_account(hass: HomeAssistant, token: dict[str, Any]) -> dict[str, Any]:
    """Validate a fresh OAuth token during the config flow."""
    access_token = token.get("access_token")
    if not access_token:
        raise GmailAuthError("No access token received")
    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with session.get(
            f"{GMAIL_API_BASE}/users/me/profile",
            headers=headers,
            timeout=30,
        ) as response:
            if response.status == HTTPStatus.UNAUTHORIZED:
                raise GmailAuthError("Google rejected the token")
            if response.status == HTTPStatus.FORBIDDEN:
                try:
                    payload = await response.json(content_type=None)
                except (ValueError, TypeError):
                    payload = None
                detail = _error_detail(response, payload)
                if "insufficient" in detail.casefold() or "scope" in detail.casefold():
                    raise GmailScopeError(detail)
                raise GmailAuthError(detail)
            if response.status >= 400:
                raise GmailError(f"Gmail API returned HTTP {response.status}")
            data = await response.json(content_type=None)
    except (ClientError, TimeoutError) as err:
        raise GmailConnectionError(
            f"Gmail is unreachable ({type(err).__name__})"
        ) from err
    if not isinstance(data, dict) or not data.get("emailAddress"):
        raise GmailError("Gmail profile could not be read")
    return data


def masked_account(profile: dict[str, Any]) -> str | None:
    account = profile.get(CONF_GMAIL_ACCOUNT) or profile.get("emailAddress")
    if not account:
        return None
    from .util import mask_email

    return mask_email(str(account))
