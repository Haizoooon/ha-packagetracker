"""Constants for the Package Tracker integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "package_tracker"
NAME: Final = "Package Tracker"
VERSION: Final = "1.0.2"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_TOKEN: Final = "token"
CONF_REDIRECT_URI: Final = "redirect_uri"
CONF_GMAIL_ACCOUNT: Final = "gmail_account"

CONF_SYNC_INTERVAL: Final = "sync_interval"
CONF_INITIAL_SYNC_DAYS: Final = "initial_sync_days"
CONF_GMAIL_QUERY: Final = "gmail_query"
CONF_MAX_MESSAGES: Final = "max_messages_per_sync"
CONF_STORE_EMAIL_SUBJECTS: Final = "store_email_subjects"
CONF_RETENTION_DAYS: Final = "retention_days"
CONF_ORDER_PLACEHOLDER_DAYS: Final = "order_placeholder_days"

CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_NOTIFY_EVENTS: Final = "notify_events"

CONF_TRACKING_PROVIDER: Final = "tracking_provider"
CONF_TRACKING_API_KEY: Final = "tracking_api_key"
CONF_TRACKING_INTERVAL: Final = "tracking_interval"
CONF_TRACKING_URL: Final = "tracking_url"
CONF_TRACKING_HEADER: Final = "tracking_header"
CONF_TRACKING_HEADER_VALUE: Final = "tracking_header_value"
CONF_TRACKING_STATUS_PATH: Final = "tracking_status_path"
CONF_TRACKING_EXPECTED_PATH: Final = "tracking_expected_path"
CONF_TRACKING_EVENTS_PATH: Final = "tracking_events_path"
CONF_TRACKING_EVENT_TIME_PATH: Final = "tracking_event_time_path"
CONF_TRACKING_EVENT_TEXT_PATH: Final = "tracking_event_text_path"
CONF_CONFIRM: Final = "confirm"
CONF_RESET_SYNC: Final = "reset_sync"
CONF_INCLUDE_COMPLETED: Final = "include_completed"
CONF_STATUS: Final = "status"
CONF_MERCHANT: Final = "merchant"
CONF_PRODUCT_NAME: Final = "product_name"
CONF_CARRIER: Final = "carrier"
CONF_TRACKING_NUMBER: Final = "tracking_number"
CONF_ORDER_NUMBER: Final = "order_number"
CONF_EXPECTED_DELIVERY: Final = "expected_delivery"
CONF_DELIVERY_WINDOW: Final = "delivery_window"
CONF_NOTES: Final = "notes"
CONF_DELIVERED_AT: Final = "delivered_at"
CONF_COMPLETED: Final = "completed"

DEFAULT_SYNC_INTERVAL: Final = 5  # minutes
DEFAULT_INITIAL_SYNC_DAYS: Final = 30
DEFAULT_MAX_MESSAGES: Final = 1000
DEFAULT_TRACKING_INTERVAL: Final = 60  # minutes, 0 = disabled
DEFAULT_RETENTION_DAYS: Final = 90  # 0 = keep forever
DEFAULT_ORDER_PLACEHOLDER_DAYS: Final = 7  # 0 = no age limit

# A deliberately broad server-side filter. The parser does the precise work.
# Gmail search is case-insensitive and searches headers and bodies.
DEFAULT_GMAIL_QUERY: Final = (
    "(from:(amazon OR dhl OR deutschepost OR deutsche-post OR hermes OR dpd OR "
    "gls-group OR ups OR fedex OR zalando OR otto OR mediamarkt OR saturn OR "
    "notebooksbilliger OR cyberport OR alternate OR mindfactory OR caseking OR "
    "apple OR ebay OR ikea OR hornbach OR bauhaus OR thalia OR rebuy OR galaxus OR "
    "aliexpress OR shein OR hm OR zara OR lidl OR aldi OR rossmann OR douglas OR "
    "samsung OR lenovo OR hp OR dell OR logitech OR sony OR microsoft) OR "
    "subject:(Sendung OR Paket OR Lieferung OR Bestellung OR Versand OR "
    "Zustellung OR Sendungsverfolgung OR Retoure OR tracking OR delivery OR "
    "shipment OR order OR parcel OR dispatch))"
)

GMAIL_SCOPE: Final = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_API_BASE: Final = "https://gmail.googleapis.com/gmail/v1"
GOOGLE_AUTHORIZE_URL: Final = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL: Final = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL: Final = "https://openidconnect.googleapis.com/v1/userinfo"

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.data"
STORAGE_SAVE_DELAY: Final = 3

MAX_PROCESSED_EMAILS: Final = 10_000
MAX_EMAIL_REFS: Final = 100
MAX_STATUS_HISTORY: Final = 200
MAX_PRODUCT_NAMES: Final = 5
MAX_BODY_CHARS: Final = 400_000

# ---------------------------------------------------------------------------
# Package status
# ---------------------------------------------------------------------------

STATUS_ORDERED: Final = "ordered"
STATUS_SHIPPED: Final = "shipped"
STATUS_IN_TRANSIT: Final = "in_transit"
STATUS_OUT_FOR_DELIVERY: Final = "out_for_delivery"
STATUS_DELIVERED: Final = "delivered"
STATUS_DELAYED: Final = "delayed"
STATUS_READY_FOR_PICKUP: Final = "ready_for_pickup"
STATUS_RETURNED: Final = "returned"
STATUS_CANCELLED: Final = "cancelled"
STATUS_UNKNOWN: Final = "unknown"

ALL_STATUSES: Final = (
    STATUS_ORDERED,
    STATUS_SHIPPED,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_DELIVERED,
    STATUS_DELAYED,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_CANCELLED,
    STATUS_UNKNOWN,
)

STATUS_RANK: Final[dict[str, int]] = {
    STATUS_UNKNOWN: 0,
    STATUS_ORDERED: 1,
    STATUS_SHIPPED: 2,
    STATUS_IN_TRANSIT: 3,
    STATUS_DELAYED: 3,
    STATUS_OUT_FOR_DELIVERY: 4,
    STATUS_READY_FOR_PICKUP: 4,
    STATUS_DELIVERED: 5,
    STATUS_RETURNED: 5,
    STATUS_CANCELLED: 5,
}

TERMINAL_STATUSES: Final = frozenset(
    {STATUS_DELIVERED, STATUS_RETURNED, STATUS_CANCELLED}
)
ACTIVE_STATUSES: Final = frozenset(
    {
        STATUS_ORDERED,
        STATUS_SHIPPED,
        STATUS_IN_TRANSIT,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELAYED,
        STATUS_READY_FOR_PICKUP,
        STATUS_UNKNOWN,
    }
)
# Statuses that mean the parcel is physically moving (used by the
# "packages in transit" sensor and the dashboard overview).
ON_THE_WAY_STATUSES: Final = frozenset(
    {
        STATUS_SHIPPED,
        STATUS_IN_TRANSIT,
        STATUS_OUT_FOR_DELIVERY,
        STATUS_DELAYED,
    }
)

STATUS_LABELS: Final[dict[str, str]] = {
    STATUS_ORDERED: "Ordered",
    STATUS_SHIPPED: "Shipped",
    STATUS_IN_TRANSIT: "In transit",
    STATUS_OUT_FOR_DELIVERY: "Out for delivery",
    STATUS_DELIVERED: "Delivered",
    STATUS_DELAYED: "Delayed",
    STATUS_READY_FOR_PICKUP: "Ready for pickup",
    STATUS_RETURNED: "Returned",
    STATUS_CANCELLED: "Cancelled",
    STATUS_UNKNOWN: "Unknown",
}

STATUS_LABELS_DE: Final[dict[str, str]] = {
    STATUS_ORDERED: "Bestellt",
    STATUS_SHIPPED: "Versendet",
    STATUS_IN_TRANSIT: "Unterwegs",
    STATUS_OUT_FOR_DELIVERY: "In Zustellung",
    STATUS_DELIVERED: "Zugestellt",
    STATUS_DELAYED: "Verspätet",
    STATUS_READY_FOR_PICKUP: "Abholbereit",
    STATUS_RETURNED: "Retourniert",
    STATUS_CANCELLED: "Storniert",
    STATUS_UNKNOWN: "Unbekannt",
}

# ---------------------------------------------------------------------------
# Carriers
# ---------------------------------------------------------------------------

CARRIER_DHL: Final = "dhl"
CARRIER_DEUTSCHE_POST: Final = "deutsche_post"
CARRIER_HERMES: Final = "hermes"
CARRIER_DPD: Final = "dpd"
CARRIER_GLS: Final = "gls"
CARRIER_UPS: Final = "ups"
CARRIER_FEDEX: Final = "fedex"
CARRIER_AMAZON: Final = "amazon_logistics"

ALL_CARRIERS: Final = (
    CARRIER_DHL,
    CARRIER_DEUTSCHE_POST,
    CARRIER_HERMES,
    CARRIER_DPD,
    CARRIER_GLS,
    CARRIER_UPS,
    CARRIER_FEDEX,
    CARRIER_AMAZON,
)

CARRIER_NAMES: Final[dict[str, str]] = {
    CARRIER_DHL: "DHL",
    CARRIER_DEUTSCHE_POST: "Deutsche Post",
    CARRIER_HERMES: "Hermes",
    CARRIER_DPD: "DPD",
    CARRIER_GLS: "GLS",
    CARRIER_UPS: "UPS",
    CARRIER_FEDEX: "FedEx",
    CARRIER_AMAZON: "Amazon Logistics",
}

# Tracking links are only built for the carrier that was detected. The link
# is a convenience, never a source of tracking data.
TRACKING_URL_TEMPLATES: Final[dict[str, str]] = {
    CARRIER_DHL: (
        "https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html"
        "?piececode={tracking}"
    ),
    CARRIER_DEUTSCHE_POST: (
        "https://www.deutschepost.de/sendung/simpleQuery.html?form_pin={tracking}"
    ),
    CARRIER_HERMES: (
        "https://www.myhermes.de/empfangen/sendungsverfolgung/"
        "sendungsinformation/#{tracking}"
    ),
    CARRIER_DPD: "https://tracking.dpd.de/status/de_DE/parcel/{tracking}",
    CARRIER_GLS: "https://gls-group.com/DE/de/paketverfolgung?match={tracking}",
    CARRIER_UPS: "https://www.ups.com/track?tracknum={tracking}",
    CARRIER_FEDEX: "https://www.fedex.com/fedextrack/?trknbr={tracking}",
    CARRIER_AMAZON: "https://track.amazon.de/tracking/{tracking}",
}

# ---------------------------------------------------------------------------
# Events, services, notifications
# ---------------------------------------------------------------------------

EVENT_PACKAGE_FOUND: Final = f"{DOMAIN}_package_found"
EVENT_PACKAGE_UPDATED: Final = f"{DOMAIN}_updated"
EVENT_PACKAGE_DELETED: Final = f"{DOMAIN}_package_deleted"

EVENT_STATUS_MAP: Final[dict[str, str]] = {
    status: f"{DOMAIN}_package_{status}" for status in ALL_STATUSES
}

EVENT_PACKAGE_ORDERED: Final = EVENT_STATUS_MAP[STATUS_ORDERED]
EVENT_PACKAGE_SHIPPED: Final = EVENT_STATUS_MAP[STATUS_SHIPPED]
EVENT_PACKAGE_IN_TRANSIT: Final = EVENT_STATUS_MAP[STATUS_IN_TRANSIT]
EVENT_PACKAGE_OUT_FOR_DELIVERY: Final = EVENT_STATUS_MAP[STATUS_OUT_FOR_DELIVERY]
EVENT_PACKAGE_DELIVERED: Final = EVENT_STATUS_MAP[STATUS_DELIVERED]
EVENT_PACKAGE_DELAYED: Final = EVENT_STATUS_MAP[STATUS_DELAYED]
EVENT_PACKAGE_READY_FOR_PICKUP: Final = EVENT_STATUS_MAP[STATUS_READY_FOR_PICKUP]
EVENT_PACKAGE_RETURNED: Final = EVENT_STATUS_MAP[STATUS_RETURNED]
EVENT_PACKAGE_CANCELLED: Final = EVENT_STATUS_MAP[STATUS_CANCELLED]

NOTIFY_EVENT_OPTIONS: Final[dict[str, str]] = {
    STATUS_ORDERED: "Order detected",
    STATUS_SHIPPED: "Parcel shipped",
    STATUS_IN_TRANSIT: "Parcel in transit",
    STATUS_OUT_FOR_DELIVERY: "Parcel out for delivery",
    STATUS_DELIVERED: "Parcel delivered",
    STATUS_DELAYED: "Parcel delayed",
    STATUS_READY_FOR_PICKUP: "Parcel ready for pickup",
    STATUS_RETURNED: "Parcel returned",
    STATUS_CANCELLED: "Order cancelled",
    STATUS_UNKNOWN: "Unknown status",
}

NOTIFY_EVENT_OPTIONS_DE: Final[dict[str, str]] = {
    STATUS_ORDERED: "Bestellung erkannt",
    STATUS_SHIPPED: "Paket versendet",
    STATUS_IN_TRANSIT: "Paket unterwegs",
    STATUS_OUT_FOR_DELIVERY: "Paket in Zustellung",
    STATUS_DELIVERED: "Paket zugestellt",
    STATUS_DELAYED: "Paket verspätet",
    STATUS_READY_FOR_PICKUP: "Paket abholbereit",
    STATUS_RETURNED: "Paket retourniert",
    STATUS_CANCELLED: "Bestellung storniert",
    STATUS_UNKNOWN: "Unbekannter Status",
}

DEFAULT_NOTIFY_EVENTS: Final = [
    STATUS_OUT_FOR_DELIVERY,
    STATUS_DELIVERED,
    STATUS_DELAYED,
    STATUS_READY_FOR_PICKUP,
]

SERVICE_SYNC: Final = "sync"
SERVICE_REFRESH: Final = "refresh"
SERVICE_REFRESH_TRACKING: Final = "refresh_tracking"
SERVICE_MARK_DELIVERED: Final = "mark_delivered"
SERVICE_MARK_COMPLETED: Final = "mark_completed"
SERVICE_UPDATE_PACKAGE: Final = "update_package"
SERVICE_DELETE_PACKAGE: Final = "delete_package"
SERVICE_DELETE_ALL: Final = "delete_all_data"
SERVICE_DISCONNECT: Final = "disconnect_account"
SERVICE_GET_PACKAGES: Final = "get_packages"

ATTR_PACKAGE_ID: Final = "package_id"
ATTR_ENTRY_ID: Final = "config_entry_id"

TRACKING_PROVIDER_NONE: Final = "none"
TRACKING_PROVIDER_DHL: Final = "dhl_unified"
TRACKING_PROVIDER_CUSTOM: Final = "custom_json"
TRACKING_PROVIDERS: Final = (
    TRACKING_PROVIDER_NONE,
    TRACKING_PROVIDER_DHL,
    TRACKING_PROVIDER_CUSTOM,
)

DHL_UNIFIED_URL: Final = "https://api-eu.dhl.com/track/shipments"

SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_SYNC_INTERVAL)
