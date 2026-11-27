"""Tests for the central package manager and merge logic."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from custom_components.package_tracker.const import (
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
)
from custom_components.package_tracker.email_parser import EmailParser, ParsedEmail
from custom_components.package_tracker.package_manager import PackageManager
from custom_components.package_tracker.util import utcnow

from .conftest import email_from_fixture, load_email_fixtures

FIXTURES = load_email_fixtures()
TZ = UTC


def parsed(key: str) -> ParsedEmail:
    result = EmailParser(TZ).parse(email_from_fixture(FIXTURES[key]))
    assert result is not None
    return result


def manager() -> PackageManager:
    # Merge tests intentionally use a long placeholder window; dedicated
    # tests below cover the production default separately.
    return PackageManager(tz=TZ, order_placeholder_days=365)


def custom(
    base: ParsedEmail,
    *,
    message_id: str,
    kind: str,
    status: str | None,
    merchant: str | None = None,
    carrier: str | None = None,
    tracking: list[str] | None = None,
    products: list[str] | None = None,
    order_numbers: list[str] | None = None,
    received_at: str | None = None,
) -> ParsedEmail:
    return replace(
        base,
        message_id=message_id,
        kind=kind,
        status=status,
        merchant=merchant,
        carrier=carrier,
        tracking_numbers=tracking or [],
        product_names=products or [],
        order_numbers=order_numbers or [],
        received_at=received_at or base.received_at,
        delivered_at=received_at if status == STATUS_DELIVERED else None,
        expected_delivery=None,
        delivery_window=None,
    )


def test_full_lifecycle_merges_into_one_package() -> None:
    mgr = manager()
    order = parsed("amazon_order")
    shipping = parsed("amazon_shipping")
    out = parsed("dhl_out_for_delivery")
    delivered = parsed("dhl_delivered")

    assert mgr.apply_parsed(order)
    assert len(mgr.shipments) == 1
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_ORDERED
    assert shipment.merchant == "Amazon"
    assert shipment.tracking_number is None
    assert "Logitech MX Master 4 kabellose Maus" in shipment.product_names

    changes = mgr.apply_parsed(shipping)
    assert changes and changes[0].shipment.id == shipment.id
    assert len(mgr.shipments) == 1
    assert shipment.status == STATUS_SHIPPED
    assert shipment.tracking_number == "00340434161094000000"
    assert shipment.expected_delivery == "2026-11-27"
    assert shipment.delivery_window == "14:00–18:00 Uhr"

    mgr.apply_parsed(out)
    assert shipment.status == STATUS_OUT_FOR_DELIVERY

    changes = mgr.apply_parsed(delivered)
    assert changes and changes[0].old_status == STATUS_OUT_FOR_DELIVERY
    assert shipment.status == STATUS_DELIVERED
    assert shipment.actual_delivery == "2026-11-26"
    assert len(mgr.shipments) == 1
    order_obj = next(iter(mgr.orders.values()))
    assert order_obj.status == STATUS_DELIVERED
    assert {event.status for event in shipment.status_history} >= {
        STATUS_ORDERED,
        STATUS_SHIPPED,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELIVERED,
    }
    assert len(shipment.emails) == 4


def test_duplicate_email_is_ignored() -> None:
    mgr = manager()
    shipping = parsed("amazon_shipping")
    assert mgr.apply_parsed(shipping)
    before = len(next(iter(mgr.shipments.values())).emails)
    assert mgr.apply_parsed(shipping) == []
    shipment = next(iter(mgr.shipments.values()))
    assert len(shipment.emails) == before


def test_repeated_status_does_not_create_new_event_loop() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    shipment = next(iter(mgr.shipments.values()))
    history_len = len(shipment.status_history)
    duplicate = replace(parsed("amazon_shipping"), message_id="new-id-same-status")
    changes = mgr.apply_parsed(duplicate)
    assert shipment.status == STATUS_SHIPPED
    assert len(shipment.status_history) == history_len
    assert changes == []


def test_multiple_parcels_in_one_order() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    order = next(iter(mgr.orders.values()))
    shipping = parsed("amazon_shipping")
    multi = replace(
        shipping,
        message_id="multi-parcel",
        tracking_numbers=["00340434161094000001", "00340434161094000002"],
        product_names=["Logitech MX Master 4", "Anker USB-C Kabel 2m"],
        expected_delivery="2026-11-29",
    )
    changes = mgr.apply_parsed(multi)
    assert len(changes) == 2
    assert len(mgr.shipments) == 2
    assert len(order.shipment_ids) == 2
    products = {s.product_name for s in mgr.shipments.values()}
    assert products == {"Logitech MX Master 4", "Anker USB-C Kabel 2m"}
    assert {s.tracking_number for s in mgr.shipments.values()} == {
        "00340434161094000001",
        "00340434161094000002",
    }


def test_two_shipping_emails_create_two_parcels() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    first = replace(
        parsed("amazon_shipping"),
        message_id="ship-1",
        tracking_numbers=["00340434161094000001"],
        product_names=["Logitech MX Master 4"],
    )
    second = replace(
        parsed("amazon_shipping"),
        message_id="ship-2",
        tracking_numbers=["00340434161094000002"],
        product_names=["Anker USB-C Kabel 2m"],
        received_at="2026-11-23T10:00:00+00:00",
    )
    mgr.apply_parsed(first)
    mgr.apply_parsed(second)
    assert len(mgr.shipments) == 2
    order = next(iter(mgr.orders.values()))
    assert len(order.shipment_ids) == 2


def test_status_never_downgrades() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    mgr.apply_parsed(parsed("dhl_out_for_delivery"))
    mgr.apply_parsed(parsed("dhl_delivered"))
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_DELIVERED
    late_update = replace(
        parsed("dhl_out_for_delivery"),
        message_id="late-update",
        received_at="2026-11-26T16:00:00+00:00",
    )
    mgr.apply_parsed(late_update)
    assert shipment.status == STATUS_DELIVERED


def test_delay_then_delivery() -> None:
    mgr = manager()
    order = parsed("dpd_shipping")
    mgr.apply_parsed(order)
    shipment = next(iter(mgr.shipments.values()))
    delay = custom(
        parsed("hermes_delay"),
        message_id="delay",
        kind="delay",
        status=STATUS_DELAYED,
        carrier="dpd",
        tracking=["09876543210987"],
        received_at="2026-11-25T09:00:00+00:00",
    )
    mgr.apply_parsed(delay)
    assert shipment.status == STATUS_DELAYED
    delivered = custom(
        parsed("dhl_delivered"),
        message_id="delivered",
        kind="delivered",
        status=STATUS_DELIVERED,
        carrier="dpd",
        tracking=["09876543210987"],
        received_at="2026-11-26T09:00:00+00:00",
    )
    mgr.apply_parsed(delivered)
    assert shipment.status == STATUS_DELIVERED


def test_pickup_status() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("dpd_shipping"))
    mgr.apply_parsed(parsed("dpd_pickup"))
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_READY_FOR_PICKUP
    assert shipment.tracking_number == "09876543210987"


def test_return_label_does_not_mark_returned() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    shipment = next(iter(mgr.shipments.values()))
    status_before = shipment.status
    mgr.apply_parsed(parsed("return_label"))
    assert shipment.status == status_before
    assert len(shipment.emails) == 2


def test_actual_return_marks_returned() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("gls_return"))
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_RETURNED
    assert shipment.carrier == "gls"


def test_cancellation_cancels_all_open_shipments() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    multi = replace(
        parsed("amazon_shipping"),
        message_id="second-parcel",
        tracking_numbers=["00340434161094000009"],
        product_names=["Anker USB-C Kabel 2m"],
    )
    mgr.apply_parsed(multi)
    cancel = custom(
        parsed("amazon_order"),
        message_id="cancel",
        kind="cancellation",
        status=STATUS_CANCELLED,
        merchant="Amazon",
        order_numbers=["302-1234567-8901234"],
    )
    changes = mgr.apply_parsed(cancel)
    assert len(changes) == 2
    assert all(s.status == STATUS_CANCELLED for s in mgr.shipments.values())


def test_missing_tracking_still_merges_by_order() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    shipment = next(iter(mgr.shipments.values()))
    update = custom(
        parsed("dhl_delivered"),
        message_id="no-tracking",
        kind="delivered",
        status=STATUS_DELIVERED,
        merchant="Amazon",
        order_numbers=["302-1234567-8901234"],
        products=["Logitech MX Master 4"],
    )
    mgr.apply_parsed(update)
    assert len(mgr.shipments) == 1
    assert shipment.status == STATUS_DELIVERED


def test_persistence_roundtrip_and_stable_ids() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    mgr.apply_parsed(parsed("dpd_shipping"))
    ids = set(mgr.shipments)
    data = mgr.to_dict()
    restored = PackageManager.from_dict(data, tz=TZ)
    assert set(restored.shipments) == ids
    assert restored.shipments[ids.pop()].status in {STATUS_SHIPPED}
    assert restored.orders
    assert restored.last_sync == mgr.last_sync
    assert restored.processed_emails.keys() == mgr.processed_emails.keys()


def test_snapshot_stats() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    mgr.apply_parsed(parsed("dpd_shipping"))
    mgr.apply_parsed(parsed("dpd_pickup"))
    mgr.apply_parsed(parsed("amazon_logistics"))
    snapshot = mgr.snapshot(utcnow())
    assert snapshot["stats"]["total"] == len(mgr.shipments)
    assert snapshot["stats"]["in_transit"] >= 1
    assert snapshot["stats"]["ready_for_pickup"] == 1
    assert snapshot["orders"]
    assert all("status_history" in package for package in snapshot["packages"])


def test_manual_update_and_delete() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("dpd_shipping"))
    shipment = next(iter(mgr.shipments.values()))
    change = mgr.update_shipment(
        shipment.id,
        merchant="MediaMarkt",
        expected_delivery="2026-12-02",
        delivery_window="09:00–12:00 Uhr",
        status=STATUS_DELAYED,
    )
    assert change is not None
    assert shipment.status == STATUS_DELAYED
    assert shipment.expected_delivery == "2026-12-02"
    assert shipment.delivery_window == "09:00–12:00 Uhr"
    assert mgr.mark_delivered(shipment.id) is not None
    assert shipment.status == STATUS_DELIVERED
    assert mgr.delete_shipment(shipment.id) is not None
    assert shipment.id not in mgr.shipments


def test_purge_only_removes_old_terminal_packages() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("amazon_order"))
    mgr.apply_parsed(parsed("amazon_shipping"))
    mgr.apply_parsed(parsed("dhl_delivered"))
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_DELIVERED
    removed = mgr.purge_terminal(90, datetime(2027, 3, 1, tzinfo=UTC))
    assert removed == 1
    assert not mgr.shipments


def test_tracking_number_only_package_has_no_order() -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("hermes_delay"))
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.tracking_number == "01234567890123"
    assert shipment.order_id is None
    assert shipment.status == STATUS_DELAYED


def test_order_confirmation_after_shipping_enriches_order() -> None:
    mgr = manager()
    shipping = parsed("amazon_shipping")
    mgr.apply_parsed(shipping)
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.status == STATUS_SHIPPED
    mgr.apply_parsed(parsed("amazon_order"))
    assert next(iter(mgr.shipments.values())).id == shipment.id
    assert shipment.status == STATUS_SHIPPED  # ordered must not downgrade
    assert len(mgr.orders) == 1
    order = next(iter(mgr.orders.values()))
    assert "Logitech MX Master 4 kabellose Maus" in order.product_names


def test_order_confirmation_adopts_early_shipping_mail() -> None:
    mgr = manager()
    shipping = replace(
        parsed("amazon_shipping"),
        message_id="early-ship",
        order_numbers=[],
        product_names=["Logitech MX Master 4 kabellose Maus"],
    )
    mgr.apply_parsed(shipping)
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.order_id is not None
    assert shipment.status == STATUS_SHIPPED

    order_confirmation = replace(
        parsed("amazon_order"),
        message_id="late-order",
        received_at="2026-11-23T09:00:00+00:00",
    )
    mgr.apply_parsed(order_confirmation)
    assert len(mgr.shipments) == 1
    assert next(iter(mgr.shipments.values())).id == shipment.id
    assert shipment.order_number == "302-1234567-8901234"
    assert len(mgr.orders) == 1
    assert next(iter(mgr.orders.values())).order_number == "302-1234567-8901234"


def test_old_order_confirmation_is_hidden_until_shipping_arrives() -> None:
    mgr = PackageManager(tz=TZ)
    old_order = replace(
        parsed("amazon_order"),
        message_id="old-order",
        received_at="2026-10-01T09:00:00+00:00",
        ordered_at="2026-10-01",
        expected_delivery=None,
    )
    assert mgr.apply_parsed(old_order) == []
    assert len(mgr.shipments) == 0
    assert len(mgr.orders) == 1

    shipping = replace(
        parsed("amazon_shipping"),
        message_id="later-shipping",
        received_at="2026-11-25T10:00:00+00:00",
    )
    changes = mgr.apply_parsed(shipping)
    assert len(changes) == 1
    assert len(mgr.shipments) == 1
    assert len(mgr.orders) == 1
    shipment = next(iter(mgr.shipments.values()))
    assert shipment.order_number == "302-1234567-8901234"
    assert shipment.status == STATUS_SHIPPED


def test_zero_order_placeholder_days_keeps_old_orders() -> None:
    mgr = PackageManager(tz=TZ, order_placeholder_days=0)
    old_order = replace(
        parsed("amazon_order"),
        message_id="old-order-visible",
        received_at="2026-10-01T09:00:00+00:00",
        ordered_at="2026-10-01",
        expected_delivery=None,
    )
    mgr.apply_parsed(old_order)
    assert len(mgr.shipments) == 1


def test_stale_order_placeholders_are_cleaned_up() -> None:
    mgr = PackageManager(tz=TZ, order_placeholder_days=365)
    old = replace(
        parsed("amazon_order"),
        message_id="stale-order",
        received_at="2026-10-01T09:00:00+00:00",
        ordered_at="2026-10-01",
        expected_delivery=None,
    )
    mgr.apply_parsed(old)
    assert len(mgr.shipments) == 1
    removed = mgr.purge_stale_order_placeholders(7, utcnow())
    assert removed == 1
    assert not mgr.shipments
