# Changelog

## 1.0.2 – 2026-11-27

- Fixed hassfest/HACS manifest key ordering.
- Added integration category and removed unsupported service translation keys.
- Added GitHub repository description/topics and brand assets for HACS/Marketplace.
- English-first documentation with German README translation.

## 1.0.1 – 2026-11-27

- Invoice, review, newsletter and coupon e-mails containing an order number are no longer treated as parcels.
- Order confirmations only appear as active parcels within the configurable **order placeholder** window (default: 7 days). Older orders are retained for later shipping matching.
- Old `ordered` placeholders without a tracking number are cleaned up automatically.
- Product names from navigation links (“Track shipment”, “My orders”, “Write a review”, …) are no longer accepted as products.
- New option `order_placeholder_days`.
- Debug logging now shows the detected mail type, merchant, carrier and counts of products/tracking numbers (without content).
- Project documentation and default UI texts are English; German translation remains available.
- Added local brand assets (`icon.png`, `logo.png`, dark and @2x variants).

## 1.0.0 – 2026-11-26

First production release.

- Gmail API (readonly) with OAuth2 config flow, reauth and automatic token refresh
- Local parser for order, shipping, tracking, delivery, delay, pickup and return e-mails
- Support for DHL, Deutsche Post, Hermes, DPD, GLS, UPS, FedEx and Amazon Logistics
- Central parcel management with orders, multiple shipments per order and stable IDs
- Persistent storage via Home Assistant `Store`
- Sensors, binary sensors, buttons and one sensor per parcel
- Events, device triggers, device conditions and device actions
- Provider-independent notifications with duplicate prevention
- Lovelace card with overview, filters, search, sorting, detail view and visual editor
- Optional DHL Unified and custom JSON tracking with error isolation
- Diagnostics redaction and repairs for auth/storage problems
- Extensive pytest and Vitest coverage with anonymised fixtures
