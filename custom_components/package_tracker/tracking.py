"""Optional external tracking providers.

The Gmail integration is the primary source.  External tracking is opt-in and
implemented with official or clearly documented endpoints only.  There is no
scraping.  Every failure is contained inside this module so it can never
break the e-mail sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_TRACKING_API_KEY,
    CONF_TRACKING_EVENT_TEXT_PATH,
    CONF_TRACKING_EVENT_TIME_PATH,
    CONF_TRACKING_EVENTS_PATH,
    CONF_TRACKING_EXPECTED_PATH,
    CONF_TRACKING_HEADER,
    CONF_TRACKING_HEADER_VALUE,
    CONF_TRACKING_INTERVAL,
    CONF_TRACKING_PROVIDER,
    CONF_TRACKING_STATUS_PATH,
    CONF_TRACKING_URL,
    DEFAULT_TRACKING_INTERVAL,
    DHL_UNIFIED_URL,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_SHIPPED,
    TRACKING_PROVIDER_CUSTOM,
    TRACKING_PROVIDER_DHL,
    TRACKING_PROVIDER_NONE,
)
from .models import PackageChange, TrackingEvent
from .package_manager import PackageManager
from .util import iso_to_date, parse_iso, truncate

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TrackingResult:
    status: str | None = None
    expected_delivery: str | None = None
    events: list[TrackingEvent] | None = None
    error: str | None = None


def _status_from_text(value: str | None) -> str | None:
    if not value:
        return None
    text = value.casefold()
    if any(token in text for token in ("zugestellt", "delivered", "delivery successful")):
        return STATUS_DELIVERED
    if any(
        token in text
        for token in ("abholbereit", "zur abholung", "packstation", "filiale", "pickup", "collection")
    ):
        return STATUS_READY_FOR_PICKUP
    if any(
        token in text
        for token in ("in zustellung", "out for delivery", "zustellfahrzeug", "beim zusteller")
    ):
        return STATUS_OUT_FOR_DELIVERY
    if any(
        token in text
        for token in (
            "verzögert",
            "verzoegert",
            "verspätet",
            "verspaetet",
            "delay",
            "delayed",
            "nicht zustellbar",
            "exception",
            "failure",
            "problem",
        )
    ):
        return STATUS_DELAYED
    if any(token in text for token in ("unterwegs", "transit", "im paketzentrum", "transport")):
        return STATUS_IN_TRANSIT
    if any(token in text for token in ("versendet", "shipped", "dispatch", "abgeholt")):
        return STATUS_SHIPPED
    return None


def _date_only(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value)
    parsed = parse_iso(text)
    if parsed is not None:
        return parsed.date().isoformat()
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        pass
    match = iso_to_date(text[:10])
    return match.isoformat() if match else None


def _resolve_path(data: Any, path: str | None) -> Any:
    if not path:
        return None
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


class TrackingProvider:
    name = "unknown"

    async def async_track(self, tracking_number: str) -> TrackingResult:
        raise NotImplementedError


class DhlUnifiedProvider(TrackingProvider):
    """DHL Shipment Tracking Unified API (official, API key required)."""

    name = TRACKING_PROVIDER_DHL

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        self._hass = hass
        self._api_key = api_key

    async def async_track(self, tracking_number: str) -> TrackingResult:
        session = async_get_clientsession(self._hass)
        headers = {"DHL-API-Key": self._api_key, "Accept": "application/json"}
        params = {"trackingNumber": tracking_number, "language": "de"}
        try:
            async with session.get(
                DHL_UNIFIED_URL, params=params, headers=headers, timeout=20
            ) as response:
                if response.status in (401, 403):
                    return TrackingResult(error="DHL API-Key ungültig oder ohne Berechtigung")
                if response.status == 404:
                    return TrackingResult(error="Sendung bei DHL nicht gefunden")
                if response.status == 429:
                    return TrackingResult(error="DHL Rate Limit erreicht")
                if response.status >= 400:
                    return TrackingResult(error=f"DHL API HTTP {response.status}")
                data = await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            return TrackingResult(error=f"DHL nicht erreichbar ({type(err).__name__})")
        except (ValueError, TypeError):
            return TrackingResult(error="Ungültige DHL Antwort")

        shipments = data.get("shipments") if isinstance(data, dict) else None
        if not isinstance(shipments, list) or not shipments:
            return TrackingResult(error="Keine Sendungsdaten von DHL")
        shipment = shipments[0] if isinstance(shipments[0], dict) else {}
        raw_events = shipment.get("events") if isinstance(shipment.get("events"), list) else []
        events: list[TrackingEvent] = []
        for raw in raw_events:
            if not isinstance(raw, dict):
                continue
            location = raw.get("location")
            location_text = None
            if isinstance(location, dict):
                address = location.get("address")
                if isinstance(address, dict):
                    location_text = address.get("addressLocality")
                location_text = location_text or location.get("name")
            events.append(
                TrackingEvent(
                    timestamp=str(raw.get("timestamp") or ""),
                    status=_status_from_text(str(raw.get("description") or raw.get("status") or "")),
                    description=truncate(str(raw.get("description") or raw.get("status") or ""), 300),
                    location=truncate(str(location_text), 120) if location_text else None,
                )
            )
        events = [event for event in events if event.timestamp]
        events.sort(key=lambda event: event.timestamp)

        status_obj = shipment.get("status") if isinstance(shipment.get("status"), dict) else {}
        description = str(status_obj.get("description") or status_obj.get("status") or "")
        status_code = str(status_obj.get("statusCode") or "")
        status = _status_from_text(description)
        if status is None:
            if status_code == "delivered":
                status = STATUS_DELIVERED
            elif status_code == "failure":
                status = STATUS_DELAYED
            elif status_code == "transit":
                status = STATUS_IN_TRANSIT
            elif status_code == "pre-transit":
                status = STATUS_SHIPPED

        expected = (
            _date_only(shipment.get("estimatedTimeOfDelivery"))
            or _date_only(shipment.get("estimatedDelivery"))
            or _date_only(shipment.get("estimatedDeliveryTime"))
        )
        return TrackingResult(status=status, expected_delivery=expected, events=events)


class CustomJsonProvider(TrackingProvider):
    """Generic JSON endpoint configured by the user.

    The endpoint contract is documented in the README.  Only plain GET
    requests are made; no JavaScript is executed and no scraping happens.
    """

    name = TRACKING_PROVIDER_CUSTOM

    def __init__(self, hass: HomeAssistant, options: dict[str, Any]) -> None:
        self._hass = hass
        self._options = options

    async def async_track(self, tracking_number: str) -> TrackingResult:
        url_template = str(self._options.get(CONF_TRACKING_URL) or "")
        if "{tracking}" not in url_template:
            return TrackingResult(error="Tracking-URL muss {tracking} enthalten")
        url = url_template.replace("{tracking}", tracking_number)
        headers = {"Accept": "application/json"}
        header_name = str(self._options.get(CONF_TRACKING_HEADER) or "").strip()
        header_value = str(self._options.get(CONF_TRACKING_HEADER_VALUE) or "").strip()
        api_key = str(self._options.get(CONF_TRACKING_API_KEY) or "").strip()
        if header_name and header_value:
            headers[header_name] = header_value
        elif api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url, headers=headers, timeout=25) as response:
                if response.status in (401, 403):
                    return TrackingResult(error="Tracking-Endpunkt verweigert den Zugriff")
                if response.status == 404:
                    return TrackingResult(error="Sendung nicht gefunden")
                if response.status == 429:
                    return TrackingResult(error="Tracking Rate Limit erreicht")
                if response.status >= 400:
                    return TrackingResult(error=f"Tracking-Endpunkt HTTP {response.status}")
                data = await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            return TrackingResult(error=f"Tracking-Endpunkt nicht erreichbar ({type(err).__name__})")
        except (ValueError, TypeError):
            return TrackingResult(error="Tracking-Endpunkt liefert kein gültiges JSON")

        status_value = _resolve_path(data, str(self._options.get(CONF_TRACKING_STATUS_PATH) or "status"))
        status = _status_from_text(str(status_value)) if status_value is not None else None
        expected = _date_only(
            _resolve_path(data, str(self._options.get(CONF_TRACKING_EXPECTED_PATH) or ""))
        )
        raw_events = _resolve_path(
            data, str(self._options.get(CONF_TRACKING_EVENTS_PATH) or "events")
        )
        events: list[TrackingEvent] = []
        if isinstance(raw_events, list):
            for raw in raw_events[:100]:
                if not isinstance(raw, dict):
                    continue
                time_value = _resolve_path(
                    raw, str(self._options.get(CONF_TRACKING_EVENT_TIME_PATH) or "timestamp")
                )
                text_value = _resolve_path(
                    raw, str(self._options.get(CONF_TRACKING_EVENT_TEXT_PATH) or "description")
                )
                if not time_value:
                    continue
                events.append(
                    TrackingEvent(
                        timestamp=str(time_value),
                        status=_status_from_text(str(text_value or "")),
                        description=truncate(str(text_value or ""), 300),
                    )
                )
        events.sort(key=lambda event: event.timestamp)
        if status is None and events:
            status = events[-1].status
        return TrackingResult(status=status, expected_delivery=expected, events=events)


def build_provider(hass: HomeAssistant, options: dict[str, Any]) -> TrackingProvider | None:
    provider = str(options.get(CONF_TRACKING_PROVIDER) or TRACKING_PROVIDER_NONE)
    if provider == TRACKING_PROVIDER_NONE:
        return None
    if provider == TRACKING_PROVIDER_DHL:
        api_key = str(options.get(CONF_TRACKING_API_KEY) or "").strip()
        if not api_key:
            _LOGGER.warning("DHL tracking is enabled but no API key is configured")
            return None
        return DhlUnifiedProvider(hass, api_key)
    if provider == TRACKING_PROVIDER_CUSTOM:
        if not options.get(CONF_TRACKING_URL):
            _LOGGER.warning("Custom tracking is enabled but no URL is configured")
            return None
        return CustomJsonProvider(hass, options)
    return None


async def async_refresh_tracking(
    hass: HomeAssistant,
    manager: PackageManager,
    options: dict[str, Any],
    *,
    force: bool = False,
    only_package_id: str | None = None,
    max_shipments: int = 20,
) -> list[PackageChange]:
    """Refresh optional tracking data.  Never raises provider errors."""
    provider = build_provider(hass, options)
    if provider is None:
        return []
    try:
        interval = max(0, int(options.get(CONF_TRACKING_INTERVAL, DEFAULT_TRACKING_INTERVAL) or 0))
    except (TypeError, ValueError):
        interval = DEFAULT_TRACKING_INTERVAL
    if interval <= 0 and not force:
        return []

    now = datetime.now(UTC)
    candidates = []
    for shipment in manager.iter_shipments():
        if only_package_id and shipment.id != only_package_id:
            continue
        if not shipment.tracking_number:
            continue
        if shipment.status in {STATUS_DELIVERED} and not force:
            continue
        if shipment.completed and not force:
            continue
        last_checked = parse_iso(shipment.tracking.last_checked) if shipment.tracking else None
        if (
            not force
            and last_checked is not None
            and (now - last_checked).total_seconds() < interval * 60
        ):
            continue
        candidates.append(shipment)
    candidates.sort(
        key=lambda shipment: shipment.tracking.last_checked if shipment.tracking else ""
    )

    changes: list[PackageChange] = []
    for shipment in candidates[:max_shipments]:
        try:
            result = await provider.async_track(shipment.tracking_number or "")
        except Exception as err:  # noqa: BLE001 - provider must never break sync
            _LOGGER.warning(
                "Tracking provider %s failed for package %s: %s",
                provider.name,
                shipment.id,
                type(err).__name__,
            )
            result = TrackingResult(error=f"Unerwarteter Fehler ({type(err).__name__})")
        if result.error:
            _LOGGER.debug(
                "Tracking failed for package %s: %s", shipment.id, result.error
            )
        change = manager.apply_tracking_update(
            shipment.id,
            provider=provider.name,
            status=result.status,
            expected_delivery=result.expected_delivery,
            events=result.events or [],
            error=result.error,
        )
        if change is not None:
            changes.append(change)
    return changes
