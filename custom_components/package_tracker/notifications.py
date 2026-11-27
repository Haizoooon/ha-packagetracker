"""Home Assistant events and optional push notifications."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_NOTIFY_EVENTS,
    CONF_NOTIFY_SERVICE,
    DEFAULT_NOTIFY_EVENTS,
    DOMAIN,
    EVENT_PACKAGE_FOUND,
    EVENT_STATUS_MAP,
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_LABELS,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
    STATUS_UNKNOWN,
)
from .models import PackageChange, Shipment
from .package_manager import PackageManager
from .util import carrier_name, iso_to_date, parse_iso

_LOGGER = logging.getLogger(__name__)


def package_unique_id(package_id: str) -> str:
    return f"{DOMAIN}_package_{package_id}"


def package_entity_id(hass: HomeAssistant, package_id: str) -> str | None:
    registry = er.async_get(hass)
    return registry.async_get_entity_id("sensor", DOMAIN, package_unique_id(package_id))


def build_event_data(
    hass: HomeAssistant,
    change: PackageChange,
    *,
    previous_status: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    shipment = change.shipment
    event_status = status or change.new_status or shipment.status
    timestamp = shipment.status_changed_at
    for history_event in reversed(shipment.status_history):
        if history_event.status == event_status and (
            change.email_id is None or history_event.email_id == change.email_id
        ):
            timestamp = history_event.timestamp
            break
    data: dict[str, Any] = {
        "package_id": shipment.id,
        "order_id": shipment.order_id,
        "merchant": shipment.merchant,
        "carrier": shipment.carrier,
        "carrier_name": carrier_name(shipment.carrier),
        "product_name": shipment.product_name,
        "product_names": list(shipment.product_names),
        "order_number": shipment.order_number,
        "tracking_number": shipment.tracking_number,
        "tracking_url": shipment.tracking_url,
        "status": event_status,
        "previous_status": previous_status,
        "expected_delivery": shipment.expected_delivery,
        "delivery_window": shipment.delivery_window,
        "actual_delivery": shipment.actual_delivery,
        "email_ids": [email.id for email in shipment.emails],
        "entity_id": package_entity_id(hass, shipment.id),
        "source": change.source,
        "timestamp": timestamp,
    }
    return data


def fire_package_events(hass: HomeAssistant, changes: list[PackageChange]) -> None:
    """Fire one found event and one status event per real change.

    The shipment object is mutable: by the time a sync is finished it can
    already have a newer status than the change being reported.  Always use
    the status captured on the change, never the object's current status.
    """
    for change in changes:
        previous = None if change.created else change.old_status
        event_status = change.new_status or change.shipment.status
        if change.created:
            hass.bus.async_fire(
                EVENT_PACKAGE_FOUND,
                build_event_data(
                    hass, change, previous_status=None, status=event_status
                ),
            )
        if not change.created and change.old_status == event_status:
            continue
        if event_status == STATUS_UNKNOWN:
            continue
        event_name = EVENT_STATUS_MAP.get(event_status)
        if event_name is None:
            continue
        hass.bus.async_fire(
            event_name,
            build_event_data(
                hass, change, previous_status=previous, status=event_status
            ),
        )


def _normalize_service(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith("notify."):
        return value.split(".", 1)[1]
    return value


def _enabled_events(options: dict[str, Any]) -> set[str]:
    raw = options.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",") if part.strip()]
    if not isinstance(raw, list):
        return set(DEFAULT_NOTIFY_EVENTS)
    return {str(value) for value in raw}


def _date_text(value: str | None) -> str | None:
    parsed = iso_to_date(value)
    if parsed is None:
        return None
    return parsed.strftime("%d.%m.%Y")


def _product_text(shipment: Shipment) -> str:
    return shipment.display_name


def _message_for(change: PackageChange) -> tuple[str, str]:
    shipment = change.shipment
    # The package object may already have advanced to a later status while
    # the notification for an earlier change is still queued.
    status = change.new_status or shipment.status
    product = _product_text(shipment)
    merchant = shipment.merchant or "deinem Shop"
    carrier = carrier_name(shipment.carrier) or "unbekanntem Paketdienst"
    date_text = _date_text(shipment.expected_delivery)
    window = shipment.delivery_window

    if status == STATUS_ORDERED:
        title = "Neue Bestellung erkannt"
        message = f"Deine Bestellung „{product}“ bei {merchant} wurde erkannt."
    elif status == STATUS_SHIPPED:
        title = "Paket versendet"
        message = f"Dein Paket „{product}“ von {merchant} wurde versendet."
        if date_text:
            message += f"\nVoraussichtliche Lieferung: {date_text}."
    elif status == STATUS_IN_TRANSIT:
        title = "Paket unterwegs"
        message = f"Dein Paket „{product}“ von {merchant} ist unterwegs."
        if date_text:
            message += f"\nVoraussichtliche Lieferung: {date_text}."
    elif status == STATUS_OUT_FOR_DELIVERY:
        title = "Paket ist in Zustellung"
        message = f"Dein Paket ist unterwegs!\n\n„{product}“ von {merchant} wird heute voraussichtlich"
        if window:
            message += f" zwischen {window.replace(' Uhr', '')} Uhr"
        message += " zugestellt."
    elif status == STATUS_DELIVERED:
        title = "Paket zugestellt"
        message = f"Dein Paket „{product}“ von {merchant} wurde zugestellt."
    elif status == STATUS_DELAYED:
        title = "Paket verspätet"
        message = f"Dein Paket „{product}“ von {merchant} verspätet sich."
        if date_text:
            message += f"\nNeuer Liefertermin: {date_text}."
    elif status == STATUS_READY_FOR_PICKUP:
        title = "Paket abholbereit"
        message = f"Dein Paket „{product}“ von {merchant} liegt zur Abholung bereit."
    elif status == STATUS_RETURNED:
        title = "Paket retourniert"
        message = f"Dein Paket „{product}“ von {merchant} wurde zurückgesandt."
    elif status == STATUS_CANCELLED:
        title = "Bestellung storniert"
        message = f"Deine Bestellung „{product}“ bei {merchant} wurde storniert."
    else:
        title = "Paket-Update"
        message = f"Status von „{product}“: {STATUS_LABELS.get(status, status)}."

    if status in {
        STATUS_SHIPPED,
        STATUS_IN_TRANSIT,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELAYED,
        STATUS_READY_FOR_PICKUP,
        STATUS_RETURNED,
    }:
        message += f"\nPaketdienst: {carrier}"
    if shipment.tracking_number and status in {
        STATUS_SHIPPED,
        STATUS_IN_TRANSIT,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELAYED,
        STATUS_READY_FOR_PICKUP,
    }:
        message += f"\nSendungsnummer: {shipment.tracking_number}"
    return title, message


async def async_handle_notifications(
    hass: HomeAssistant,
    manager: PackageManager,
    changes: list[PackageChange],
    options: dict[str, Any],
) -> None:
    """Send notifications through the normal Home Assistant notify service."""
    service = _normalize_service(options.get(CONF_NOTIFY_SERVICE))
    if not service:
        return
    enabled = _enabled_events(options)
    if not enabled:
        return
    if not hass.services.has_service("notify", service):
        _LOGGER.warning(
            "Configured notify service notify.%s does not exist; skipping notification",
            service,
        )
        return

    # If one sync catches up on several status changes for the same parcel
    # (e.g. ordered -> shipped -> delivered), only notify the latest eligible
    # change instead of sending a burst of old pushes.
    latest: dict[str, PackageChange] = {}
    for change in changes:
        shipment = change.shipment
        status = change.new_status or shipment.status
        if status == STATUS_UNKNOWN or status not in enabled:
            continue
        if not change.created and change.old_status == status:
            continue
        latest[shipment.id] = change

    for change in latest.values():
        shipment = change.shipment
        status = change.new_status or shipment.status
        if manager.notification_already_sent(shipment.id, status):
            continue
        # Do not flood the user with pushes for the initial historical import.
        # Events still fire for automations; only push notifications are
        # suppressed for e-mails older than 48 hours.
        last_email = parse_iso(
            shipment.last_email_at or change.shipment.status_changed_at
        )
        if change.source == "email" and last_email is not None:
            age = (datetime.now(UTC) - last_email).total_seconds()
            if age > 48 * 3600:
                continue
        title, message = _message_for(change)
        data: dict[str, Any] = {}
        if service.startswith("mobile_app_"):
            data["tag"] = f"package_tracker_{shipment.id}_{status}"
            data["group"] = "package_tracker"
            if shipment.tracking_url:
                data["url"] = shipment.tracking_url
                data["clickAction"] = shipment.tracking_url
        payload: dict[str, Any] = {"title": title, "message": message}
        if data:
            payload["data"] = data
        try:
            await hass.services.async_call(
                "notify",
                service,
                payload,
                blocking=False,
            )
            manager.mark_notification_sent(shipment.id, status)
        except Exception as err:  # noqa: BLE001 - notifications are optional
            _LOGGER.warning(
                "Could not send package notification via notify.%s: %s",
                service,
                type(err).__name__,
            )


def format_event_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return None
