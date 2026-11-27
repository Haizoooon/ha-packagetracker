"""Data model for Package Tracker.

The integration deliberately keeps *orders* and *shipments* separate.  An
order can consist of several shipments, and a shipment is what the dashboard
shows as a package.  Both objects are plain dataclasses so they can be
serialised to Home Assistant's Store without any ORM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .const import (
    ACTIVE_STATUSES,
    ALL_STATUSES,
    CARRIER_NAMES,
    MAX_EMAIL_REFS,
    MAX_PRODUCT_NAMES,
    MAX_STATUS_HISTORY,
    STATUS_CANCELLED,
    STATUS_DELIVERED,
    STATUS_LABELS,
    STATUS_RANK,
    STATUS_RETURNED,
    STATUS_UNKNOWN,
    TERMINAL_STATUSES,
)


def _as_str(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        return value or default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


@dataclass(slots=True)
class EmailRef:
    """Metadata of a processed e-mail.  Bodies are never stored."""

    id: str
    received_at: str
    kind: str = "unknown"
    subject: str | None = None
    sender: str | None = None
    status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> EmailRef | None:
        data = _as_dict(data)
        email_id = _as_str(data.get("id"))
        if not email_id:
            return None
        return cls(
            id=email_id,
            received_at=_as_str(data.get("received_at"), "") or "",
            kind=_as_str(data.get("kind"), "unknown") or "unknown",
            subject=_as_str(data.get("subject")),
            sender=_as_str(data.get("sender")),
            status=_as_str(data.get("status")),
        )


@dataclass(slots=True)
class StatusEvent:
    """One entry in the status history of a shipment."""

    status: str
    timestamp: str
    source: str = "email"
    message: str | None = None
    email_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> StatusEvent | None:
        data = _as_dict(data)
        status = _as_str(data.get("status"))
        timestamp = _as_str(data.get("timestamp"))
        if status not in ALL_STATUSES or not timestamp:
            return None
        return cls(
            status=status,
            timestamp=timestamp,
            source=_as_str(data.get("source"), "email") or "email",
            message=_as_str(data.get("message")),
            email_id=_as_str(data.get("email_id")),
        )


@dataclass(slots=True)
class TrackingEvent:
    """A tracking event from an external tracking provider."""

    timestamp: str
    status: str | None = None
    description: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Any) -> TrackingEvent | None:
        data = _as_dict(data)
        timestamp = _as_str(data.get("timestamp"))
        if not timestamp:
            return None
        return cls(
            timestamp=timestamp,
            status=_as_str(data.get("status")),
            description=_as_str(data.get("description")),
            location=_as_str(data.get("location")),
        )


@dataclass(slots=True)
class TrackingInfo:
    """Data from an optional external tracking provider.

    Kept strictly separate from e-mail derived data.  It never overwrites
    order data, product data or a terminal e-mail status.
    """

    provider: str
    last_checked: str | None = None
    status: str | None = None
    expected_delivery: str | None = None
    events: list[TrackingEvent] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "last_checked": self.last_checked,
            "status": self.status,
            "expected_delivery": self.expected_delivery,
            "events": [event.to_dict() for event in self.events],
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Any) -> TrackingInfo | None:
        data = _as_dict(data)
        provider = _as_str(data.get("provider"))
        if not provider:
            return None
        events: list[TrackingEvent] = []
        for raw in _as_list(data.get("events")):
            event = TrackingEvent.from_dict(raw)
            if event is not None:
                events.append(event)
        return cls(
            provider=provider,
            last_checked=_as_str(data.get("last_checked")),
            status=_as_str(data.get("status")),
            expected_delivery=_as_str(data.get("expected_delivery")),
            events=events[-100:],
            error=_as_str(data.get("error")),
        )


@dataclass(slots=True)
class Shipment:
    """A physical parcel.  This is the main object shown by the dashboard."""

    id: str
    order_id: str | None = None
    merchant: str | None = None
    carrier: str | None = None
    product_name: str | None = None
    product_names: list[str] = field(default_factory=list)
    product_image: str | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    order_date: str | None = None
    shipped_date: str | None = None
    expected_delivery: str | None = None
    delivery_window: str | None = None
    actual_delivery: str | None = None
    status: str = STATUS_UNKNOWN
    status_changed_at: str | None = None
    status_history: list[StatusEvent] = field(default_factory=list)
    emails: list[EmailRef] = field(default_factory=list)
    last_email_at: str | None = None
    last_email_subject: str | None = None
    last_email_from: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    completed: bool = False
    notes: str | None = None
    tracking: TrackingInfo | None = None
    source: str = "gmail"
    manual_override: bool = False

    # -- derived helpers ---------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        return not self.completed and self.status in ACTIVE_STATUSES

    @property
    def display_name(self) -> str:
        if self.product_name:
            return self.product_name
        if self.product_names:
            return self.product_names[0]
        if self.merchant:
            return f"Paket von {self.merchant}"
        return "Paket"

    @property
    def label(self) -> str:
        name = self.display_name
        merchant = self.merchant or "Unknown merchant"
        return f"{name} – {merchant}"

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def status_rank(self) -> int:
        return STATUS_RANK.get(self.status, 0)

    def add_product_names(self, names: list[str]) -> bool:
        """Merge product names, keeping the most specific name first."""
        changed = False
        existing = list(self.product_names)
        normalized = {
            name.casefold().strip(): name for name in existing if name.strip()
        }
        for name in names:
            clean = name.strip()
            if not clean:
                continue
            key = clean.casefold()
            if key in normalized:
                continue
            existing.append(clean)
            normalized[key] = clean
            changed = True
        if changed:
            self.product_names = existing[:MAX_PRODUCT_NAMES]
        if not self.product_name and self.product_names:
            self.product_name = self.product_names[0]
            changed = True
        elif self.product_name:
            # Keep the current primary name but make sure it is in the list.
            if self.product_name.casefold().strip() not in {
                name.casefold().strip() for name in self.product_names
            }:
                self.product_names.insert(0, self.product_name)
                self.product_names = self.product_names[:MAX_PRODUCT_NAMES]
        return changed

    def add_status_event(
        self,
        status: str,
        timestamp: str,
        *,
        source: str = "email",
        message: str | None = None,
        email_id: str | None = None,
    ) -> None:
        event = StatusEvent(
            status=status,
            timestamp=timestamp,
            source=source,
            message=message,
            email_id=email_id,
        )
        # Avoid identical consecutive entries (repeated status e-mails).
        if self.status_history:
            last = self.status_history[-1]
            if (
                last.status == event.status
                and last.timestamp == event.timestamp
                and last.message == event.message
            ):
                return
        self.status_history.append(event)
        self.status_history = self.status_history[-MAX_STATUS_HISTORY:]

    def add_email(self, email: EmailRef) -> bool:
        if any(existing.id == email.id for existing in self.emails):
            return False
        self.emails.append(email)
        self.emails = self.emails[-MAX_EMAIL_REFS:]
        self.last_email_at = email.received_at
        self.last_email_subject = email.subject
        self.last_email_from = email.sender
        return True

    def tracking_history(self) -> list[dict[str, Any]]:
        """Serialise tracking data for the dashboard.

        E-mail events and provider events stay visibly separated.
        """
        if self.tracking is None:
            return []
        return [
            {
                "timestamp": event.timestamp,
                "status": event.status,
                "description": event.description,
                "location": event.location,
                "source": "tracking",
            }
            for event in self.tracking.events
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "merchant": self.merchant,
            "carrier": self.carrier,
            "product_name": self.product_name,
            "product_names": list(self.product_names),
            "product_image": self.product_image,
            "order_number": self.order_number,
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "order_date": self.order_date,
            "shipped_date": self.shipped_date,
            "expected_delivery": self.expected_delivery,
            "delivery_window": self.delivery_window,
            "actual_delivery": self.actual_delivery,
            "status": self.status,
            "status_changed_at": self.status_changed_at,
            "status_history": [event.to_dict() for event in self.status_history],
            "emails": [email.to_dict() for email in self.emails],
            "last_email_at": self.last_email_at,
            "last_email_subject": self.last_email_subject,
            "last_email_from": self.last_email_from,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed": self.completed,
            "notes": self.notes,
            "tracking": self.tracking.to_dict() if self.tracking else None,
            "source": self.source,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Shipment | None:
        data = _as_dict(data)
        shipment_id = _as_str(data.get("id"))
        if not shipment_id:
            return None

        status = _as_str(data.get("status"), STATUS_UNKNOWN) or STATUS_UNKNOWN
        if status not in ALL_STATUSES:
            status = STATUS_UNKNOWN

        history: list[StatusEvent] = []
        for raw in _as_list(data.get("status_history")):
            event = StatusEvent.from_dict(raw)
            if event is not None:
                history.append(event)
        history = history[-MAX_STATUS_HISTORY:]

        emails: list[EmailRef] = []
        for raw in _as_list(data.get("emails")):
            email = EmailRef.from_dict(raw)
            if email is not None:
                emails.append(email)
        emails = emails[-MAX_EMAIL_REFS:]

        product_names = [
            name for name in _as_list(data.get("product_names")) if isinstance(name, str)
        ][:MAX_PRODUCT_NAMES]

        return cls(
            id=shipment_id,
            order_id=_as_str(data.get("order_id")),
            merchant=_as_str(data.get("merchant")),
            carrier=_as_str(data.get("carrier")),
            product_name=_as_str(data.get("product_name")),
            product_names=product_names,
            product_image=_as_str(data.get("product_image")),
            order_number=_as_str(data.get("order_number")),
            tracking_number=_as_str(data.get("tracking_number")),
            tracking_url=_as_str(data.get("tracking_url")),
            order_date=_as_str(data.get("order_date")),
            shipped_date=_as_str(data.get("shipped_date")),
            expected_delivery=_as_str(data.get("expected_delivery")),
            delivery_window=_as_str(data.get("delivery_window")),
            actual_delivery=_as_str(data.get("actual_delivery")),
            status=status,
            status_changed_at=_as_str(data.get("status_changed_at")),
            status_history=history,
            emails=emails,
            last_email_at=_as_str(data.get("last_email_at")),
            last_email_subject=_as_str(data.get("last_email_subject")),
            last_email_from=_as_str(data.get("last_email_from")),
            created_at=_as_str(data.get("created_at")),
            updated_at=_as_str(data.get("updated_at")),
            completed=_as_bool(data.get("completed")),
            notes=_as_str(data.get("notes")),
            tracking=TrackingInfo.from_dict(data.get("tracking")),
            source=_as_str(data.get("source"), "gmail") or "gmail",
            manual_override=_as_bool(data.get("manual_override")),
        )


@dataclass(slots=True)
class Order:
    """A merchant order that can consist of one or more shipments."""

    id: str
    merchant: str | None = None
    order_number: str | None = None
    order_date: str | None = None
    product_names: list[str] = field(default_factory=list)
    product_image: str | None = None
    shipment_ids: list[str] = field(default_factory=list)
    emails: list[EmailRef] = field(default_factory=list)
    status: str = STATUS_UNKNOWN
    created_at: str | None = None
    updated_at: str | None = None

    def recompute_status(self, shipments: list[Shipment]) -> None:
        if not shipments:
            self.status = STATUS_UNKNOWN
            return
        statuses = [shipment.status for shipment in shipments]
        if all(status == STATUS_DELIVERED for status in statuses):
            self.status = STATUS_DELIVERED
            return
        active = [
            shipment for shipment in shipments if shipment.status not in TERMINAL_STATUSES
        ]
        if active:
            # An order with one delivered and one in-transit parcel is still
            # in transit, not delivered.
            self.status = max(
                (shipment.status for shipment in active),
                key=lambda value: STATUS_RANK.get(value, 0),
            )
        elif any(status == STATUS_RETURNED for status in statuses):
            self.status = STATUS_RETURNED
        elif any(status == STATUS_CANCELLED for status in statuses):
            self.status = STATUS_CANCELLED
        else:
            self.status = STATUS_DELIVERED

    def add_email(self, email: EmailRef) -> None:
        if any(existing.id == email.id for existing in self.emails):
            return
        self.emails.append(email)
        self.emails = self.emails[-MAX_EMAIL_REFS:]

    def add_product_names(self, names: list[str]) -> None:
        existing = {name.casefold() for name in self.product_names}
        for name in names:
            if name.strip() and name.casefold() not in existing:
                self.product_names.append(name.strip())
                existing.add(name.casefold())
        self.product_names = self.product_names[:MAX_PRODUCT_NAMES]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "merchant": self.merchant,
            "order_number": self.order_number,
            "order_date": self.order_date,
            "product_names": list(self.product_names),
            "product_image": self.product_image,
            "shipment_ids": list(self.shipment_ids),
            "emails": [email.to_dict() for email in self.emails],
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Order | None:
        data = _as_dict(data)
        order_id = _as_str(data.get("id"))
        if not order_id:
            return None
        emails: list[EmailRef] = []
        for raw in _as_list(data.get("emails")):
            email = EmailRef.from_dict(raw)
            if email is not None:
                emails.append(email)
        status = _as_str(data.get("status"), STATUS_UNKNOWN) or STATUS_UNKNOWN
        if status not in ALL_STATUSES:
            status = STATUS_UNKNOWN
        return cls(
            id=order_id,
            merchant=_as_str(data.get("merchant")),
            order_number=_as_str(data.get("order_number")),
            order_date=_as_str(data.get("order_date")),
            product_names=[
                name
                for name in _as_list(data.get("product_names"))
                if isinstance(name, str)
            ][:MAX_PRODUCT_NAMES],
            product_image=_as_str(data.get("product_image")),
            shipment_ids=[
                value
                for value in _as_list(data.get("shipment_ids"))
                if isinstance(value, str)
            ],
            emails=emails[-MAX_EMAIL_REFS:],
            status=status,
            created_at=_as_str(data.get("created_at")),
            updated_at=_as_str(data.get("updated_at")),
        )


@dataclass(slots=True)
class PackageChange:
    """Internal change notification used for events and push notifications."""

    shipment: Shipment
    created: bool = False
    old_status: str | None = None
    new_status: str | None = None
    source: str = "email"
    email_id: str | None = None

    @property
    def status_changed(self) -> bool:
        return (
            self.new_status is not None
            and self.old_status is not None
            and self.new_status != self.old_status
        )


def shipment_frontend_dict(
    shipment: Shipment,
    *,
    order: Order | None = None,
    siblings: list[Shipment] | None = None,
    include_history: bool = True,
) -> dict[str, Any]:
    """Build the shared payload consumed by websocket API and sensors.

    This is the *single* representation of a package for all consumers.
    """
    payload = shipment.to_dict()
    payload.update(
        {
            "status_label": shipment.status_label,
            "display_name": shipment.display_name,
            "is_active": shipment.is_active,
            "is_terminal": shipment.is_terminal,
            "carrier_name": CARRIER_NAMES.get(shipment.carrier or "", shipment.carrier),
            "tracking_events": shipment.tracking_history(),
            "order": order.to_dict() if order else None,
            "siblings": [
                {
                    "id": sibling.id,
                    "tracking_number": sibling.tracking_number,
                    "carrier": sibling.carrier,
                    "status": sibling.status,
                    "product_name": sibling.display_name,
                    "expected_delivery": sibling.expected_delivery,
                }
                for sibling in (siblings or [])
                if sibling.id != shipment.id
            ],
        }
    )
    if not include_history:
        payload.pop("status_history", None)
        payload.pop("tracking_events", None)
    return payload


__all__ = [
    "MAX_EMAIL_REFS",
    "EmailRef",
    "Order",
    "PackageChange",
    "Shipment",
    "StatusEvent",
    "TrackingEvent",
    "TrackingInfo",
    "shipment_frontend_dict",
]
