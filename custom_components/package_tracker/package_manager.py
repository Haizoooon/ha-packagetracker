"""Central package management.

All consumers (sensors, websocket API, services, notifications) use the
objects managed here.  There is exactly one persistence layer and exactly one
merge implementation.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any

from .const import (
    ACTIVE_STATUSES,
    MAX_PROCESSED_EMAILS,
    MAX_PRODUCT_NAMES,
    ON_THE_WAY_STATUSES,
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
    STATUS_UNKNOWN,
    TERMINAL_STATUSES,
)
from .email_parser import ParsedEmail
from .models import (
    EmailRef,
    Order,
    PackageChange,
    Shipment,
    shipment_frontend_dict,
)
from .util import (
    build_tracking_url,
    iso_to_date,
    local_date,
    mask_email,
    normalize_key,
    normalize_tracking,
    parse_iso,
    truncate,
    utcnow,
    utcnow_iso,
)

_LOGGER = logging.getLogger(__name__)

_STOPWORDS = {
    "der",
    "die",
    "das",
    "und",
    "mit",
    "für",
    "fuer",
    "von",
    "the",
    "and",
    "with",
    "for",
    "pack",
    "stück",
    "stueck",
    "stk",
}


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:20]}"


def _tracking_key(value: str | None) -> str:
    return normalize_tracking(value)


class PackageManager:
    """Owns orders, shipments and processed-email bookkeeping."""

    def __init__(
        self,
        *,
        store_email_subjects: bool = True,
        shipments: dict[str, Shipment] | None = None,
        orders: dict[str, Order] | None = None,
        processed_emails: dict[str, str] | None = None,
        last_sync: str | None = None,
        gmail_account: str | None = None,
        last_notified: dict[str, str] | None = None,
        tz: tzinfo | None = None,
    ) -> None:
        self.store_email_subjects = store_email_subjects
        self.tz: tzinfo = tz or UTC
        self.shipments: dict[str, Shipment] = shipments or {}
        self.orders: dict[str, Order] = orders or {}
        self.processed_emails: dict[str, str] = processed_emails or {}
        self.last_sync = last_sync
        self.gmail_account = gmail_account
        self.last_notified = last_notified or {}
        self._repair_links()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        *,
        store_email_subjects: bool = True,
        tz: tzinfo | None = None,
    ) -> PackageManager:
        data = data or {}
        shipments: dict[str, Shipment] = {}
        for raw in data.get("shipments", []) if isinstance(data, dict) else []:
            shipment = Shipment.from_dict(raw)
            if shipment is None:
                continue
            shipments[shipment.id] = shipment
        orders: dict[str, Order] = {}
        for raw in data.get("orders", []) if isinstance(data, dict) else []:
            order = Order.from_dict(raw)
            if order is None:
                continue
            orders[order.id] = order
        processed_raw = data.get("processed_emails") if isinstance(data, dict) else {}
        processed: dict[str, str] = {}
        if isinstance(processed_raw, dict):
            for key, value in list(processed_raw.items())[-MAX_PROCESSED_EMAILS:]:
                if isinstance(key, str):
                    processed[key] = value if isinstance(value, str) else ""
        elif isinstance(processed_raw, list):
            for item in processed_raw[-MAX_PROCESSED_EMAILS:]:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    processed[item["id"]] = str(item.get("received_at", ""))
        last_notified = data.get("last_notified") if isinstance(data, dict) else {}
        if not isinstance(last_notified, dict):
            last_notified = {}
        return cls(
            store_email_subjects=store_email_subjects,
            shipments=shipments,
            orders=orders,
            processed_emails=processed,
            last_sync=data.get("last_sync") if isinstance(data, dict) else None,
            gmail_account=data.get("gmail_account") if isinstance(data, dict) else None,
            last_notified={
                key: value
                for key, value in last_notified.items()
                if isinstance(key, str) and isinstance(value, str)
            },
            tz=tz,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "created_at": utcnow_iso(),
            "shipments": [shipment.to_dict() for shipment in self.shipments.values()],
            "orders": [order.to_dict() for order in self.orders.values()],
            "processed_emails": self.processed_emails,
            "last_sync": self.last_sync,
            "gmail_account": self.gmail_account,
            "last_notified": self.last_notified,
        }

    def _repair_links(self) -> None:
        """Drop dangling links and rebuild order shipment lists."""
        for shipment in self.shipments.values():
            if shipment.order_id and shipment.order_id not in self.orders:
                shipment.order_id = None
        for order in self.orders.values():
            order.shipment_ids = list(
                dict.fromkeys(
                    shipment_id
                    for shipment_id in order.shipment_ids
                    if shipment_id in self.shipments
                )
            )
        for shipment in self.shipments.values():
            if shipment.order_id and shipment.id not in self.orders[shipment.order_id].shipment_ids:
                self.orders[shipment.order_id].shipment_ids.append(shipment.id)
        # Remove orders that only exist because of a broken link and have no
        # e-mail evidence at all.
        for order_id in list(self.orders):
            order = self.orders[order_id]
            if not order.shipment_ids and not order.emails:
                del self.orders[order_id]

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_shipment(self, package_id: str) -> Shipment | None:
        return self.shipments.get(package_id)

    def get_order(self, order_id: str | None) -> Order | None:
        if not order_id:
            return None
        return self.orders.get(order_id)

    def iter_shipments(self) -> Iterable[Shipment]:
        return self.shipments.values()

    def find_by_tracking(self, tracking: str) -> Shipment | None:
        key = _tracking_key(tracking)
        if not key:
            return None
        for shipment in self.shipments.values():
            if _tracking_key(shipment.tracking_number) == key:
                return shipment
        return None

    def was_processed(self, email_id: str) -> bool:
        return email_id in self.processed_emails

    def mark_processed(self, email_id: str, received_at: str) -> None:
        self.processed_emails[email_id] = received_at
        if len(self.processed_emails) > MAX_PROCESSED_EMAILS:
            # Keep the newest entries; dicts preserve insertion order.
            overflow = len(self.processed_emails) - MAX_PROCESSED_EMAILS
            for key in list(self.processed_emails)[:overflow]:
                self.processed_emails.pop(key, None)

    # ------------------------------------------------------------------
    # E-mail ingestion
    # ------------------------------------------------------------------

    def apply_parsed(self, parsed: ParsedEmail) -> list[PackageChange]:
        """Merge one parsed e-mail into the package graph."""
        if self.was_processed(parsed.message_id):
            return []

        email_ref = EmailRef(
            id=parsed.message_id,
            received_at=parsed.received_at,
            kind=parsed.kind,
            subject=parsed.subject if self.store_email_subjects else None,
            sender=parsed.sender or None,
            status=parsed.status,
        )
        self.mark_processed(parsed.message_id, parsed.received_at)

        # A return label does not mean the parcel was returned.
        if parsed.kind == "return_label":
            order = self._find_order(parsed)
            if order is not None:
                order.add_email(email_ref)
                order.updated_at = utcnow_iso()
                shipment = self._find_shipment(parsed, order)
                if shipment is not None:
                    shipment.add_email(email_ref)
                    shipment.notes = parsed.notes or shipment.notes
                    shipment.updated_at = utcnow_iso()
            return []

        shipment = self._find_shipment_by_tracking(parsed)
        order = self.get_order(shipment.order_id) if shipment else None
        if shipment is None:
            order = order or self._find_order(parsed)
            if order is not None:
                shipment = self._find_shipment(parsed, order)

        if parsed.kind == "cancellation" and shipment is None:
            order = order or self._find_order(parsed)
            if order is not None:
                affected = self._cancel_order_shipments(order, email_ref, parsed)
                if affected:
                    return affected
                order.add_email(email_ref)
                order.updated_at = utcnow_iso()
                return []
            if not (parsed.order_numbers or parsed.merchant):
                return []

        if shipment is None:
            shipment = self._find_shipment_fallback(parsed)
            if shipment is not None:
                order = self.get_order(shipment.order_id) or order

        if shipment is None:
            shipment = self._create_shipment(parsed, order)
            if shipment is None:
                return []
            order = self.get_order(shipment.order_id) or order
            created = True
        else:
            created = False
            if order is None:
                order = self._find_order(parsed)
            if order is None and shipment.order_id:
                order = self.get_order(shipment.order_id)

        if order is None:
            order = self._ensure_order(parsed, shipment)
        elif shipment.order_id != order.id:
            shipment.order_id = order.id
            if shipment.id not in order.shipment_ids:
                order.shipment_ids.append(shipment.id)

        # A cancellation usually concerns the whole order, not just the one
        # parcel whose tracking number happened to be mentioned.
        if parsed.kind == "cancellation" and order is not None:
            cancelled = self._cancel_order_shipments(order, email_ref, parsed)
            if cancelled:
                return cancelled

        changes: list[PackageChange] = []
        change = self._apply_to_shipment(shipment, parsed, email_ref, order, created=created)
        if change is not None:
            changes.append(change)

        self._apply_additional_tracking_numbers(parsed, shipment, order, email_ref, changes)

        if order is not None:
            order.add_email(email_ref)
            if parsed.merchant and not order.merchant:
                order.merchant = parsed.merchant
            order.add_product_names(parsed.product_names)
            if not order.product_image and parsed.product_image:
                order.product_image = parsed.product_image
            if order.order_date is None and parsed.ordered_at:
                order.order_date = parsed.ordered_at
            order.updated_at = utcnow_iso()
            self._recompute_order(order)
            for change_item in changes:
                if change_item.shipment.order_id == order.id:
                    change_item.shipment.updated_at = utcnow_iso()
        return changes

    def _find_order(self, parsed: ParsedEmail) -> Order | None:
        for number in parsed.order_numbers:
            number_key = normalize_key(number)
            for order in self.orders.values():
                if order.order_number and normalize_key(order.order_number) == number_key:
                    if (
                        not parsed.merchant
                        or not order.merchant
                        or normalize_key(order.merchant) == normalize_key(parsed.merchant)
                    ):
                        return order
        # A new order confirmation must never be merged into an unrelated
        # open order of the same merchant just because the merchant matches.
        if parsed.kind == "order_confirmation" and not parsed.order_numbers:
            return None
        if parsed.merchant or parsed.tracking_numbers:
            candidates = self._open_orders_for_merchant(parsed.merchant)
            if len(candidates) == 1 and parsed.kind not in {
                "order_confirmation",
                "cancellation",
            }:
                return candidates[0]
            if len(candidates) > 1 and parsed.product_names:
                scored = [
                    (_similarity(parsed.product_names, order.product_names), order)
                    for order in candidates
                ]
                scored.sort(key=lambda item: item[0], reverse=True)
                if scored and scored[0][0] >= 0.65:
                    if len(scored) == 1 or scored[1][0] < scored[0][0] - 0.15:
                        return scored[0][1]
        return None

    def _open_orders_for_merchant(self, merchant: str | None) -> list[Order]:
        if not merchant:
            return []
        merchant_key = normalize_key(merchant)
        result: list[Order] = []
        for order in self.orders.values():
            if normalize_key(order.merchant) != merchant_key:
                continue
            shipments = [s for s in self.shipments.values() if s.order_id == order.id]
            if shipments and all(s.status in TERMINAL_STATUSES for s in shipments):
                continue
            result.append(order)
        return result

    def _find_shipment_by_tracking(self, parsed: ParsedEmail) -> Shipment | None:
        for number in parsed.tracking_numbers:
            shipment = self.find_by_tracking(number)
            if shipment is not None:
                return shipment
        return None

    def _find_shipment(self, parsed: ParsedEmail, order: Order) -> Shipment | None:
        candidates = [
            self.shipments[shipment_id]
            for shipment_id in order.shipment_ids
            if shipment_id in self.shipments
        ]
        if not candidates:
            return None

        for number in parsed.tracking_numbers:
            shipment = self.find_by_tracking(number)
            if shipment is not None and shipment.order_id == order.id:
                return shipment

        if parsed.tracking_numbers:
            without_tracking = [s for s in candidates if not s.tracking_number]
            if without_tracking:
                return self._best_product_match(parsed, without_tracking) or without_tracking[0]
            return None

        if parsed.kind == "cancellation":
            return None

        active = [s for s in candidates if s.status not in TERMINAL_STATUSES]
        match = self._best_product_match(parsed, active or candidates)
        if match is not None:
            return match
        if len(active) == 1:
            return active[0]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _find_shipment_fallback(self, parsed: ParsedEmail) -> Shipment | None:
        if parsed.kind in {"cancellation", "return_label"}:
            return None
        # An unknown tracking number means a new parcel, not a status update
        # for an existing one.  Tracking matches were already checked.
        if parsed.tracking_numbers:
            return None
        if parsed.kind == "order_confirmation":
            # If the shipping mail was imported before the order confirmation
            # (e.g. after a long initial backfill), adopt that parcel into the
            # confirmed order instead of creating a duplicate.  Require a
            # unique, specific product match.
            if not parsed.product_names:
                return None
            candidates = [
                shipment
                for shipment in self.shipments.values()
                if (not parsed.merchant or not shipment.merchant or normalize_key(parsed.merchant) == normalize_key(shipment.merchant))
                and not shipment.completed
            ]
            scored = sorted(
                (
                    (_similarity(parsed.product_names, shipment.product_names), shipment)
                    for shipment in candidates
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            if scored and scored[0][0] >= 0.75:
                if len(scored) == 1 or scored[1][0] < scored[0][0] - 0.1:
                    return scored[0][1]
            return None

        now = utcnow()
        today_local = datetime.now(self.tz).date()
        recent_candidates: list[Shipment] = []
        for shipment in self.shipments.values():
            if shipment.status in TERMINAL_STATUSES and parsed.status != STATUS_RETURNED:
                continue
            if parsed.merchant and shipment.merchant:
                if normalize_key(parsed.merchant) != normalize_key(shipment.merchant):
                    continue
            elif parsed.merchant and not shipment.merchant:
                pass
            last = parse_iso(shipment.last_email_at or shipment.updated_at)
            if last is not None and now - last > timedelta(days=45):
                continue
            if parsed.carrier and shipment.carrier:
                if parsed.carrier != shipment.carrier:
                    continue
            recent_candidates.append(shipment)

        if not recent_candidates:
            return None

        match = self._best_product_match(parsed, recent_candidates)
        if match is not None:
            return match

        active = [s for s in recent_candidates if s.status not in TERMINAL_STATUSES]
        if len(active) == 1:
            return active[0]
        if parsed.carrier and parsed.merchant:
            same = [
                s
                for s in active
                if s.carrier == parsed.carrier
                and normalize_key(s.merchant) == normalize_key(parsed.merchant)
            ]
            if len(same) == 1:
                return same[0]
        # Carrier status mails sometimes contain neither a tracking number nor
        # an order number.  Attaching to the single recent parcel for that
        # carrier is safer than creating a duplicate.  Do this only for
        # delivery related mails and only when it is unambiguous.
        if parsed.kind in {
            "delivery_announcement",
            "tracking_update",
            "delay",
            "pickup",
            "delivered",
        }:
            carrier_candidates = [
                s
                for s in active
                if (not parsed.carrier or s.carrier == parsed.carrier)
                and (
                    s.expected_delivery
                    and iso_to_date(s.expected_delivery) is not None
                    and abs((iso_to_date(s.expected_delivery) - today_local).days) <= 10
                )
            ]
            if len(carrier_candidates) == 1:
                return carrier_candidates[0]
        return None

    def _best_product_match(
        self, parsed: ParsedEmail, candidates: list[Shipment]
    ) -> Shipment | None:
        if not parsed.product_names or not candidates:
            return None
        scored = [
            (_similarity(parsed.product_names, shipment.product_names), shipment)
            for shipment in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored or scored[0][0] < 0.6:
            return None
        if len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.1:
            return None
        return scored[0][1]

    def _ensure_order(
        self, parsed: ParsedEmail, shipment: Shipment | None = None
    ) -> Order | None:
        if shipment is not None and shipment.order_id and shipment.order_id in self.orders:
            return self.orders[shipment.order_id]
        if not parsed.merchant and not parsed.order_numbers:
            return None

        order_number = parsed.order_numbers[0] if parsed.order_numbers else None
        if order_number:
            order_id = _make_id(
                "ord", f"{normalize_key(parsed.merchant)}|{normalize_key(order_number)}"
            )
        else:
            order_id = _make_id(
                "ord",
                f"{normalize_key(parsed.merchant)}|{parsed.thread_id or parsed.message_id}",
            )
        now = utcnow_iso()
        order = self.orders.get(order_id)
        if order is None:
            order = Order(
                id=order_id,
                merchant=parsed.merchant,
                order_number=order_number,
                order_date=parsed.ordered_at,
                product_names=list(parsed.product_names),
                product_image=parsed.product_image,
                created_at=now,
                updated_at=now,
            )
            self.orders[order_id] = order
        else:
            if parsed.merchant and not order.merchant:
                order.merchant = parsed.merchant
            order.add_product_names(parsed.product_names)
        if shipment is not None:
            shipment.order_id = order.id
            if shipment.id not in order.shipment_ids:
                order.shipment_ids.append(shipment.id)
        return order

    def _create_shipment(
        self, parsed: ParsedEmail, order: Order | None
    ) -> Shipment | None:
        if order is None:
            order = self._ensure_order(parsed)
        if order is None and not (parsed.merchant or parsed.tracking_numbers):
            return None

        if parsed.tracking_numbers:
            shipment_id = _make_id(
                "pkg",
                f"track|{parsed.carrier}|{_tracking_key(parsed.tracking_numbers[0])}",
            )
        elif order is not None:
            seq = len(order.shipment_ids)
            shipment_id = _make_id("pkg", f"order|{order.id}|{seq}")
        else:
            shipment_id = _make_id("pkg", f"mail|{parsed.message_id}")

        if shipment_id in self.shipments:
            return self.shipments[shipment_id]

        now = utcnow_iso()
        shipment = Shipment(
            id=shipment_id,
            order_id=order.id if order else None,
            merchant=parsed.merchant or (order.merchant if order else None),
            carrier=parsed.carrier,
            product_names=list(parsed.product_names),
            product_name=parsed.product_names[0] if parsed.product_names else None,
            product_image=parsed.product_image,
            order_number=(order.order_number if order else None)
            or (parsed.order_numbers[0] if parsed.order_numbers else None),
            tracking_number=parsed.tracking_numbers[0] if parsed.tracking_numbers else None,
            tracking_url=parsed.tracking_url,
            created_at=now,
            updated_at=now,
            status=STATUS_UNKNOWN,
            status_changed_at=now,
        )
        self.shipments[shipment_id] = shipment
        if order is not None:
            if shipment.id not in order.shipment_ids:
                order.shipment_ids.append(shipment.id)
            order.updated_at = now
        return shipment

    def _apply_to_shipment(
        self,
        shipment: Shipment,
        parsed: ParsedEmail,
        email_ref: EmailRef,
        order: Order | None,
        *,
        created: bool,
    ) -> PackageChange | None:
        old_status = shipment.status
        now = utcnow_iso()
        email_date = local_date(parse_iso(parsed.received_at), self.tz)

        if parsed.merchant and not shipment.merchant:
            shipment.merchant = parsed.merchant
        if parsed.carrier and not shipment.carrier:
            shipment.carrier = parsed.carrier
        if parsed.order_numbers and not shipment.order_number:
            shipment.order_number = parsed.order_numbers[0]
        if not shipment.order_id and order is not None:
            shipment.order_id = order.id

        if parsed.tracking_numbers:
            primary = self._primary_tracking_for(shipment, parsed.tracking_numbers)
            if not shipment.tracking_number and primary:
                shipment.tracking_number = primary
            if parsed.tracking_url and (
                not shipment.tracking_url or primary == parsed.tracking_numbers[0]
            ):
                shipment.tracking_url = parsed.tracking_url
            if not shipment.tracking_url:
                shipment.tracking_url = build_tracking_url(
                    shipment.carrier, shipment.tracking_number
                )

        shipment.add_product_names(parsed.product_names)
        if not shipment.product_image and parsed.product_image:
            shipment.product_image = parsed.product_image

        if parsed.ordered_at and not shipment.order_date:
            shipment.order_date = parsed.ordered_at
        if parsed.shipped_at and not shipment.shipped_date:
            shipment.shipped_date = parsed.shipped_at
        if parsed.expected_delivery:
            if not shipment.expected_delivery or parsed.kind != "order_confirmation":
                if parsed.status in {
                    STATUS_DELIVERED,
                    STATUS_DELAYED,
                    STATUS_OUT_FOR_DELIVERY,
                    STATUS_READY_FOR_PICKUP,
                    STATUS_IN_TRANSIT,
                    STATUS_SHIPPED,
                } or not shipment.expected_delivery:
                    shipment.expected_delivery = parsed.expected_delivery
        if parsed.delivery_window:
            shipment.delivery_window = parsed.delivery_window
        if parsed.notes:
            shipment.notes = truncate(parsed.notes, 200)

        new_status = parsed.status
        status_changed = False
        if new_status and self._can_transition(shipment.status, new_status):
            shipment.status = new_status
            shipment.status_changed_at = parsed.received_at or now
            status_changed = True
        elif new_status and shipment.status == new_status:
            status_changed = False

        if shipment.status == STATUS_DELIVERED:
            if parsed.delivered_at:
                shipment.actual_delivery = parsed.delivered_at
            elif not shipment.actual_delivery:
                shipment.actual_delivery = email_date
            shipment.completed = False
        if shipment.status == STATUS_DELAYED and parsed.expected_delivery:
            shipment.expected_delivery = parsed.expected_delivery

        if status_changed:
            shipment.add_status_event(
                shipment.status,
                parsed.received_at or now,
                source="email",
                message=parsed.notes,
                email_id=parsed.message_id,
            )
        elif parsed.kind in {"tracking_update", "delivery_announcement", "delay"}:
            last_event = shipment.status_history[-1] if shipment.status_history else None
            if last_event is None or last_event.email_id != parsed.message_id:
                shipment.add_status_event(
                    shipment.status,
                    parsed.received_at or now,
                    source="email",
                    message=parsed.notes,
                    email_id=parsed.message_id,
                )

        shipment.add_email(email_ref)
        shipment.updated_at = now
        if order is not None and parsed.merchant and not order.merchant:
            order.merchant = parsed.merchant

        # Only real state changes produce an event.  Repeated status e-mails
        # still enrich the record and append their e-mail reference, but they
        # must never trigger a duplicate notification.
        if created or status_changed:
            return PackageChange(
                shipment=shipment,
                created=created,
                old_status=old_status if not created else None,
                new_status=shipment.status,
                source="email",
                email_id=parsed.message_id,
            )
        return None

    def _primary_tracking_for(
        self, shipment: Shipment, tracking_numbers: list[str]
    ) -> str | None:
        if not tracking_numbers:
            return None
        current = _tracking_key(shipment.tracking_number)
        for number in tracking_numbers:
            if _tracking_key(number) == current:
                return number
        return tracking_numbers[0]

    def _apply_additional_tracking_numbers(
        self,
        parsed: ParsedEmail,
        primary_shipment: Shipment,
        order: Order | None,
        email_ref: EmailRef,
        changes: list[PackageChange],
    ) -> None:
        if len(parsed.tracking_numbers) <= 1:
            return
        primary_key = _tracking_key(primary_shipment.tracking_number)
        additional = [
            number
            for number in parsed.tracking_numbers[1:]
            if _tracking_key(number) != primary_key
        ]
        if not additional:
            return

        product_count = len(parsed.product_names)
        tracking_count = len(parsed.tracking_numbers)
        if product_count == tracking_count and tracking_count > 1:
            # Assign products to parcels by position when the merchant sends
            # one e-mail per multi-parcel order.
            primary_name = parsed.product_names[0]
            primary_shipment.product_name = primary_name
            primary_shipment.product_names = [primary_name]

        for index, number in enumerate(additional, start=1):
            existing = self.find_by_tracking(number)
            single = replace(parsed, tracking_numbers=[number])
            if existing is not None:
                change = self._apply_to_shipment(
                    existing, single, email_ref, order, created=False
                )
                if change is not None:
                    changes.append(change)
                continue
            product_names: list[str] = []
            if product_count == tracking_count:
                product_names = [parsed.product_names[index]]
            sibling = replace(
                parsed,
                tracking_numbers=[number],
                product_names=product_names,
                product_image=parsed.product_image if product_names else None,
            )
            shipment = self._create_shipment(sibling, order)
            if shipment is None:
                continue
            if order is not None and shipment.id not in order.shipment_ids:
                order.shipment_ids.append(shipment.id)
            change = self._apply_to_shipment(
                shipment, sibling, email_ref, order, created=True
            )
            if change is not None:
                changes.append(change)

    def _can_transition(self, old: str, new: str) -> bool:
        if old == new:
            return False
        if old in TERMINAL_STATUSES:
            return False
        allowed: dict[str, set[str]] = {
            STATUS_ORDERED: {STATUS_UNKNOWN},
            STATUS_SHIPPED: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
            },
            STATUS_IN_TRANSIT: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_DELAYED,
            },
            STATUS_DELAYED: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_OUT_FOR_DELIVERY,
                STATUS_READY_FOR_PICKUP,
            },
            STATUS_OUT_FOR_DELIVERY: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_DELAYED,
            },
            STATUS_READY_FOR_PICKUP: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_OUT_FOR_DELIVERY,
                STATUS_DELAYED,
            },
            STATUS_DELIVERED: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_DELAYED,
                STATUS_OUT_FOR_DELIVERY,
                STATUS_READY_FOR_PICKUP,
            },
            STATUS_RETURNED: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_DELAYED,
                STATUS_OUT_FOR_DELIVERY,
                STATUS_READY_FOR_PICKUP,
                STATUS_DELIVERED,
            },
            STATUS_CANCELLED: {
                STATUS_UNKNOWN,
                STATUS_ORDERED,
                STATUS_SHIPPED,
                STATUS_IN_TRANSIT,
                STATUS_DELAYED,
                STATUS_OUT_FOR_DELIVERY,
                STATUS_READY_FOR_PICKUP,
            },
        }
        return old in allowed.get(new, set())

    def _cancel_order_shipments(
        self, order: Order, email_ref: EmailRef, parsed: ParsedEmail
    ) -> list[PackageChange]:
        changes: list[PackageChange] = []
        now = utcnow_iso()
        for shipment_id in list(order.shipment_ids):
            shipment = self.shipments.get(shipment_id)
            if shipment is None or shipment.status in TERMINAL_STATUSES:
                continue
            old_status = shipment.status
            shipment.status = STATUS_CANCELLED
            shipment.status_changed_at = parsed.received_at or now
            shipment.updated_at = now
            shipment.add_status_event(
                STATUS_CANCELLED,
                parsed.received_at or now,
                source="email",
                message="Bestellung storniert",
                email_id=parsed.message_id,
            )
            shipment.add_email(email_ref)
            shipment.completed = False
            changes.append(
                PackageChange(
                    shipment=shipment,
                    created=False,
                    old_status=old_status,
                    new_status=STATUS_CANCELLED,
                    source="email",
                    email_id=parsed.message_id,
                )
            )
        order.add_email(email_ref)
        order.updated_at = now
        self._recompute_order(order)
        return changes

    def _recompute_order(self, order: Order) -> None:
        shipments = [
            self.shipments[shipment_id]
            for shipment_id in order.shipment_ids
            if shipment_id in self.shipments
        ]
        order.recompute_status(shipments)
        if not order.merchant:
            for shipment in shipments:
                if shipment.merchant:
                    order.merchant = shipment.merchant
                    break
        if not order.order_number:
            for shipment in shipments:
                if shipment.order_number:
                    order.order_number = shipment.order_number
                    break

    def apply_tracking_update(
        self,
        package_id: str,
        *,
        provider: str,
        status: str | None,
        expected_delivery: str | None,
        events: list[Any],
        error: str | None,
    ) -> PackageChange | None:
        """Store optional tracking provider data without touching e-mail facts.

        Tracking data lives in ``shipment.tracking``.  Only a status that fits
        the state machine and a delivery estimate are merged into the main
        fields; product, merchant, order and e-mail history stay untouched.
        """
        from .models import TrackingInfo

        shipment = self.shipments.get(package_id)
        if shipment is None:
            return None
        now = utcnow_iso()
        tracking = TrackingInfo(
            provider=provider,
            last_checked=now,
            status=status,
            expected_delivery=expected_delivery,
            events=events[-100:],
            error=error,
        )
        shipment.tracking = tracking
        shipment.updated_at = now
        if error or not status:
            return None

        old_status = shipment.status
        changed = False
        if self._can_transition(shipment.status, status):
            shipment.status = status
            shipment.status_changed_at = now
            shipment.add_status_event(
                status,
                now,
                source="tracking",
                message="Tracking-Update",
            )
            changed = True
        if status == STATUS_DELIVERED and not shipment.actual_delivery:
            shipment.actual_delivery = local_date(utcnow(), self.tz)
        if expected_delivery and (
            not shipment.expected_delivery or status in {STATUS_DELAYED, STATUS_OUT_FOR_DELIVERY}
        ):
            shipment.expected_delivery = expected_delivery

        order = self.get_order(shipment.order_id)
        if order is not None:
            self._recompute_order(order)
            order.updated_at = now
        if changed:
            return PackageChange(
                shipment=shipment,
                created=False,
                old_status=old_status,
                new_status=shipment.status,
                source="tracking",
            )
        return None

    # ------------------------------------------------------------------
    # Manual operations
    # ------------------------------------------------------------------

    def mark_delivered(
        self, package_id: str, delivered_at: str | None = None
    ) -> PackageChange | None:
        shipment = self.shipments.get(package_id)
        if shipment is None:
            return None
        now = utcnow_iso()
        old_status = shipment.status
        if old_status == STATUS_DELIVERED:
            return None
        shipment.status = STATUS_DELIVERED
        shipment.status_changed_at = now
        shipment.actual_delivery = delivered_at or local_date(utcnow(), self.tz)
        shipment.updated_at = now
        shipment.manual_override = True
        shipment.add_status_event(
            STATUS_DELIVERED, now, source="manual", message="Manuell als zugestellt markiert"
        )
        order = self.get_order(shipment.order_id)
        if order is not None:
            self._recompute_order(order)
            order.updated_at = now
        return PackageChange(
            shipment=shipment,
            created=False,
            old_status=old_status,
            new_status=STATUS_DELIVERED,
            source="manual",
        )

    def mark_completed(self, package_id: str, completed: bool = True) -> Shipment | None:
        shipment = self.shipments.get(package_id)
        if shipment is None:
            return None
        shipment.completed = completed
        shipment.updated_at = utcnow_iso()
        return shipment

    def update_shipment(self, package_id: str, **fields: Any) -> PackageChange | None:
        shipment = self.shipments.get(package_id)
        if shipment is None:
            return None
        now = utcnow_iso()
        old_status = shipment.status
        status_changed = False

        allowed = {
            "merchant",
            "carrier",
            "product_name",
            "product_image",
            "order_number",
            "tracking_number",
            "tracking_url",
            "expected_delivery",
            "delivery_window",
            "notes",
            "completed",
            "status",
        }
        for key, value in fields.items():
            if key not in allowed or value is None:
                continue
            if key == "status":
                if value not in {STATUS_UNKNOWN, *ACTIVE_STATUSES, *TERMINAL_STATUSES}:
                    continue
                if value != shipment.status:
                    shipment.status = value
                    shipment.status_changed_at = now
                    shipment.manual_override = True
                    status_changed = True
                    shipment.add_status_event(
                        value, now, source="manual", message="Status manuell geändert"
                    )
                continue
            setattr(shipment, key, value)
            if key == "product_name":
                remaining = [
                    name
                    for name in shipment.product_names
                    if name.casefold() != str(value).casefold()
                ]
                shipment.product_names = [str(value), *remaining][
                    :MAX_PRODUCT_NAMES
                ]
            shipment.manual_override = True
        if fields.get("tracking_number") and not fields.get("tracking_url"):
            shipment.tracking_url = build_tracking_url(
                shipment.carrier, shipment.tracking_number
            )
        if fields.get("carrier") and not fields.get("tracking_url"):
            shipment.tracking_url = build_tracking_url(
                shipment.carrier, shipment.tracking_number
            )
        shipment.updated_at = now
        if shipment.status == STATUS_DELIVERED and not shipment.actual_delivery:
            shipment.actual_delivery = local_date(utcnow(), self.tz)
        order = self.get_order(shipment.order_id)
        if order is not None:
            self._recompute_order(order)
            order.updated_at = now
        return PackageChange(
            shipment=shipment,
            created=False,
            old_status=old_status,
            new_status=shipment.status,
            source="manual",
        ) if status_changed else None

    def delete_shipment(self, package_id: str) -> Shipment | None:
        shipment = self.shipments.pop(package_id, None)
        if shipment is None:
            return None
        order = self.get_order(shipment.order_id)
        if order is not None:
            order.shipment_ids = [
                value for value in order.shipment_ids if value != package_id
            ]
            if order.shipment_ids:
                self._recompute_order(order)
                order.updated_at = utcnow_iso()
            else:
                # Do not leave an order shell behind after its last parcel was
                # deleted or purged.
                self.orders.pop(order.id, None)
        self.last_notified = {
            key: value
            for key, value in self.last_notified.items()
            if not key.startswith(f"{package_id}:")
        }
        return shipment

    def purge_terminal(self, retention_days: int, today: datetime) -> int:
        if retention_days <= 0:
            return 0
        cutoff = today.date() - timedelta(days=retention_days)
        removed = 0
        for shipment_id, shipment in list(self.shipments.items()):
            if shipment.status not in TERMINAL_STATUSES and not shipment.completed:
                continue
            reference = (
                iso_to_date(shipment.actual_delivery)
                or iso_to_date(shipment.status_changed_at)
                or iso_to_date(shipment.updated_at)
            )
            if reference is None or reference > cutoff:
                continue
            self.delete_shipment(shipment_id)
            removed += 1
        return removed

    def clear(self, *, reset_sync: bool = False) -> None:
        self.shipments.clear()
        self.orders.clear()
        if reset_sync:
            self.processed_emails.clear()
            self.last_sync = None
        self.last_notified.clear()

    # ------------------------------------------------------------------
    # Notifications bookkeeping
    # ------------------------------------------------------------------

    def notification_already_sent(
        self, package_id: str, event: str, *, window_hours: int = 12
    ) -> bool:
        key = f"{package_id}:{event}"
        last = parse_iso(self.last_notified.get(key))
        if last is None:
            return False
        return utcnow() - last < timedelta(hours=window_hours)

    def mark_notification_sent(self, package_id: str, event: str) -> None:
        key = f"{package_id}:{event}"
        self.last_notified[key] = utcnow_iso()
        if len(self.last_notified) > 2000:
            for old_key in list(self.last_notified)[:500]:
                self.last_notified.pop(old_key, None)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, now: datetime) -> dict[str, Any]:
        today = now.date().isoformat()
        packages: list[dict[str, Any]] = []
        for shipment in self.shipments.values():
            order = self.get_order(shipment.order_id)
            siblings = []
            if order is not None:
                siblings = [
                    self.shipments[sid]
                    for sid in order.shipment_ids
                    if sid in self.shipments and sid != shipment.id
                ]
            packages.append(
                shipment_frontend_dict(
                    shipment, order=order, siblings=siblings, include_history=True
                )
            )

        packages.sort(
            key=lambda item: (
                item.get("is_terminal", False),
                item.get("expected_delivery") or "9999-12-31",
                item.get("created_at") or "",
            )
        )

        active = [
            item
            for item in packages
            if not item.get("completed") and not item.get("is_terminal")
        ]
        in_transit = [
            item
            for item in active
            if item.get("status") in ON_THE_WAY_STATUSES
        ]
        delivery_today = [
            item
            for item in active
            if item.get("expected_delivery") == today
        ]
        delivered_today = [
            item
            for item in packages
            if item.get("status") == STATUS_DELIVERED
            and item.get("actual_delivery") == today
        ]
        delayed = [item for item in active if item.get("status") == STATUS_DELAYED]
        ready_for_pickup = [
            item for item in active if item.get("status") == STATUS_READY_FOR_PICKUP
        ]
        upcoming = [
            item
            for item in active
            if item.get("expected_delivery")
            and item["expected_delivery"] >= today
            and item.get("status") != STATUS_READY_FOR_PICKUP
        ]
        upcoming.sort(key=lambda item: item.get("expected_delivery") or "9999-12-31")
        next_delivery = upcoming[0] if upcoming else None

        orders = [order.to_dict() for order in self.orders.values()]
        stats = {
            "total": len(packages),
            "active": len(active),
            "in_transit": len(in_transit),
            "delivery_today": len(delivery_today),
            "delivered_today": len(delivered_today),
            "delayed": len(delayed),
            "ready_for_pickup": len(ready_for_pickup),
            "next_delivery": next_delivery,
        }

        return {
            "version": 1,
            "generated_at": utcnow_iso(),
            "packages": packages,
            "orders": orders,
            "stats": stats,
            "gmail": {
                "connected": bool(self.gmail_account),
                "account": mask_email(self.gmail_account),
                "last_sync": self.last_sync,
                "emails_processed": len(self.processed_emails),
            },
        }

    def package_payload(self, package_id: str) -> dict[str, Any] | None:
        shipment = self.shipments.get(package_id)
        if shipment is None:
            return None
        order = self.get_order(shipment.order_id)
        siblings = []
        if order is not None:
            siblings = [
                self.shipments[sid]
                for sid in order.shipment_ids
                if sid in self.shipments and sid != shipment.id
            ]
        return shipment_frontend_dict(
            shipment, order=order, siblings=siblings, include_history=True
        )


def _similarity(left: list[str], right: list[str]) -> float:
    """Token based similarity used for product/order merging."""
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    exact = 1.0 if normalize_key(" ".join(left)) == normalize_key(" ".join(right)) else 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    jaccard = len(intersection) / len(union) if union else 0.0
    containment = 0.0
    if left_tokens and right_tokens:
        containment = len(intersection) / min(len(left_tokens), len(right_tokens))
    # Substring match catches "MX Master 4" vs "Logitech MX Master 4 Maus".
    substring = 0.0
    for a in left:
        for b in right:
            na, nb = normalize_key(a), normalize_key(b)
            if len(na) >= 5 and len(nb) >= 5 and (na in nb or nb in na):
                substring = max(substring, 0.8)
    return max(exact, jaccard, containment * 0.9, substring)


def _tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in normalize_key(value).split():
            if len(token) >= 3 and token not in _STOPWORDS:
                tokens.add(token)
    return tokens


__all__ = ["PackageManager"]
