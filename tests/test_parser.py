"""Tests for local e-mail analysis and carrier recognition."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.package_tracker.const import (
    CARRIER_AMAZON,
    CARRIER_DHL,
    CARRIER_DPD,
    CARRIER_GLS,
    CARRIER_HERMES,
    CARRIER_UPS,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
)
from custom_components.package_tracker.email_parser import EmailMessage, EmailParser
from custom_components.package_tracker.util import (
    find_expected_delivery,
    find_time_window,
)

from .conftest import email_from_fixture, load_email_fixtures

FIXTURES = load_email_fixtures()


def parse(key: str):
    email = email_from_fixture(FIXTURES[key])
    return EmailParser(UTC).parse(email)


def test_amazon_order_is_recognised() -> None:
    parsed = parse("amazon_order")
    assert parsed is not None
    assert parsed.kind == "order_confirmation"
    assert parsed.status == STATUS_ORDERED
    assert parsed.merchant == "Amazon"
    assert parsed.order_numbers == ["302-1234567-8901234"]
    assert "Logitech MX Master 4 kabellose Maus" in parsed.product_names
    assert any("Anker USB-C Kabel" in name for name in parsed.product_names)
    assert parsed.product_image == "https://m.media-amazon.com/images/I/61mxmaster.jpg"
    assert parsed.expected_delivery == "2026-11-27"
    assert parsed.tracking_numbers == []


def test_amazon_shipping_matches_dhl_and_extracts_window() -> None:
    parsed = parse("amazon_shipping")
    assert parsed is not None
    assert parsed.kind == "shipping_confirmation"
    assert parsed.status == STATUS_SHIPPED
    assert parsed.carrier == CARRIER_DHL
    assert parsed.tracking_numbers == ["00340434161094000000"]
    assert parsed.order_numbers == ["302-1234567-8901234"]
    assert parsed.expected_delivery == "2026-11-27"
    assert parsed.delivery_window == "14:00–18:00 Uhr"
    assert "Logitech MX Master 4" in " ".join(parsed.product_names)
    assert parsed.tracking_url and "dhl.de" in parsed.tracking_url


def test_out_for_delivery_is_not_mistaken_for_delivered() -> None:
    parsed = parse("dhl_out_for_delivery")
    assert parsed is not None
    assert parsed.kind == "delivery_announcement"
    assert parsed.status == STATUS_OUT_FOR_DELIVERY
    assert parsed.carrier == CARRIER_DHL
    assert parsed.tracking_numbers == ["00340434161094000000"]
    assert parsed.expected_delivery == "2026-11-26"
    assert parsed.delivery_window == "14:00–18:00 Uhr"


def test_delivered_mail_sets_actual_date() -> None:
    parsed = parse("dhl_delivered")
    assert parsed is not None
    assert parsed.kind == "delivered"
    assert parsed.status == STATUS_DELIVERED
    assert parsed.delivered_at == "2026-11-26"
    assert parsed.carrier == CARRIER_DHL


def test_hermes_delay_and_new_date() -> None:
    parsed = parse("hermes_delay")
    assert parsed is not None
    assert parsed.kind == "delay"
    assert parsed.status == STATUS_DELAYED
    assert parsed.carrier == CARRIER_HERMES
    assert parsed.tracking_numbers == ["01234567890123"]
    assert parsed.expected_delivery == "2026-11-28"


def test_dpd_shipping_uses_merchant_from_body() -> None:
    parsed = parse("dpd_shipping")
    assert parsed is not None
    assert parsed.status == STATUS_SHIPPED
    assert parsed.carrier == CARRIER_DPD
    assert parsed.merchant == "MediaMarkt"
    assert parsed.tracking_numbers == ["09876543210987"]
    assert parsed.order_numbers == ["DPD-998877"]
    assert parsed.expected_delivery == "2026-11-25"


def test_dpd_pickup() -> None:
    parsed = parse("dpd_pickup")
    assert parsed is not None
    assert parsed.kind == "pickup"
    assert parsed.status == STATUS_READY_FOR_PICKUP
    assert parsed.carrier == CARRIER_DPD
    assert parsed.tracking_numbers == ["09876543210987"]


def test_ups_tracking_and_merchant() -> None:
    parsed = parse("ups_shipped")
    assert parsed is not None
    assert parsed.carrier == CARRIER_UPS
    assert parsed.tracking_numbers == ["1Z999AA10123456784"]
    assert parsed.merchant == "Cyberport"
    assert parsed.order_numbers == ["CY-2026-4455"]
    assert parsed.expected_delivery == "2026-11-29"


def test_amazon_logistics_tba() -> None:
    parsed = parse("amazon_logistics")
    assert parsed is not None
    assert parsed.carrier == CARRIER_AMAZON
    assert parsed.tracking_numbers == ["TBA123456789012"]
    assert parsed.status == STATUS_OUT_FOR_DELIVERY
    assert parsed.expected_delivery == "2026-11-26"


def test_return_label_is_not_a_returned_parcel() -> None:
    parsed = parse("return_label")
    assert parsed is not None
    assert parsed.kind == "return_label"
    assert parsed.status is None
    assert parsed.order_numbers == ["302-1234567-8901234"]


def test_gls_return() -> None:
    parsed = parse("gls_return")
    assert parsed is not None
    assert parsed.carrier == CARRIER_GLS
    assert parsed.status == STATUS_RETURNED
    assert parsed.tracking_numbers == ["12345678901234"]


def test_marketing_mail_is_ignored() -> None:
    assert parse("marketing") is None


def test_malformed_html_does_not_crash() -> None:
    parsed = parse("malformed")
    assert parsed is not None
    assert parsed.status == STATUS_SHIPPED
    assert parsed.tracking_numbers == ["00340434161094000000"]
    assert parsed.product_names


def test_empty_message_is_ignored() -> None:
    email = EmailMessage(
        id="empty",
        thread_id=None,
        received_at=datetime.now(UTC),
        sender_name="",
        sender_email="",
        subject="",
        text="",
        html="",
    )
    assert EmailParser(UTC).parse(email) is None


def test_date_and_window_helpers() -> None:
    reference = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
    assert (
        find_expected_delivery(
            "Voraussichtliche Zustellung: 27.11.2026",
            "Ihre Sendung",
            reference,
        )
        == "2026-11-27"
    )
    assert (
        find_expected_delivery(
            "Die Zustellung erfolgt morgen.",
            "Ihre Sendung",
            reference,
        )
        == "2026-11-25"
    )
    assert find_time_window("Zustellung zwischen 14:00 und 18:00 Uhr") == "14:00–18:00 Uhr"
    assert find_time_window("Hotline 8-20 Uhr") is None


def test_no_false_positive_tracking_from_order_number() -> None:
    parsed = parse("amazon_order")
    assert parsed is not None
    assert parsed.tracking_numbers == []
    assert all("302-1234567" not in number for number in parsed.tracking_numbers)


def test_deutsche_post_support() -> None:
    parsed = parse("deutsche_post_shipped")
    assert parsed is not None
    assert parsed.carrier == "deutsche_post"
    assert parsed.status == STATUS_SHIPPED
    assert parsed.tracking_numbers == ["RR123456789DE"]
    assert parsed.expected_delivery == "2026-11-30"


def test_fedex_support() -> None:
    parsed = parse("fedex_delivered")
    assert parsed is not None
    assert parsed.carrier == "fedex"
    assert parsed.status == STATUS_DELIVERED
    assert parsed.tracking_numbers == ["123456789012"]
    assert parsed.delivered_at == "2026-11-26"


def test_future_delivery_announcement_is_not_out_for_delivery_yet() -> None:
    email = EmailMessage(
        id="future",
        thread_id=None,
        received_at=datetime(2026, 11, 24, 9, 0, tzinfo=UTC),
        sender_name="Amazon.de",
        sender_email="versand@amazon.de",
        subject="Ihre Bestellung wird am 29.11.2026 zugestellt",
        text="Ihre Bestellung wird am 29.11.2026 zugestellt. Bestellnummer: 302-1234567-8901234",
        html="",
    )
    parsed = EmailParser(UTC).parse(email)
    assert parsed is not None
    assert parsed.status == "in_transit"
    assert parsed.expected_delivery == "2026-11-29"


def test_review_request_with_order_number_is_not_a_package() -> None:
    email = EmailMessage(
        id="review",
        thread_id=None,
        received_at=datetime(2026, 11, 24, 9, 0, tzinfo=UTC),
        sender_name="Amazon.de",
        sender_email="bewertung@amazon.de",
        subject="Bewerte deine Bestellung von Logitech MX Master 4",
        text=(
            "Vielen Dank für deine Bestellung. Wie war dein Produkt? "
            "Bestellnummer: 302-1234567-8901234. Jetzt bewerten."
        ),
        html="",
    )
    assert EmailParser(UTC).parse(email) is None


def test_invoice_mail_with_order_number_is_not_a_package() -> None:
    email = EmailMessage(
        id="invoice",
        thread_id=None,
        received_at=datetime(2026, 11, 24, 9, 0, tzinfo=UTC),
        sender_name="Amazon.de",
        sender_email="rechnung@amazon.de",
        subject="Deine Rechnung für Bestellung 302-1234567-8901234",
        text=(
            "Vielen Dank für deine Bestellung. Im Anhang findest du deine Rechnung. "
            "Bestellnummer: 302-1234567-8901234."
        ),
        html="",
    )
    assert EmailParser(UTC).parse(email) is None


@pytest.mark.parametrize(
    "subject",
    [
        "Ablageort buchen",
        "Amazon Haul: 15% auf Besteller",
        "Angebote shoppen",
        "Apple Produkte & Zubehör - Deals",
        "Bis zu 30 % auf Amazon Marken",
        "Black Friday Angebote",
        "Black Friday Woche",
        "Der Freshty Day Shop",
    ],
)
def test_marketing_subjects_are_never_parcels(subject: str) -> None:
    email = EmailMessage(
        id="marketing-subject",
        thread_id=None,
        received_at=datetime(2026, 11, 24, 9, 0, tzinfo=UTC),
        sender_name="Amazon.de",
        sender_email="newsletter@amazon.de",
        subject=subject,
        text=(
            "Sendungsnummer: 00340434161094000000. "
            "Ihre Sendung ist unterwegs. Bestellnummer: 302-1234567-8901234. "
            "Jetzt Angebote entdecken."
        ),
        html="",
    )
    assert EmailParser(UTC).parse(email) is None
