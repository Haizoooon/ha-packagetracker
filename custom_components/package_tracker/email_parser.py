"""Local, rule based e-mail analysis.

No e-mail content ever leaves Home Assistant.  The parser turns a Gmail
message into a small :class:`ParsedEmail` value object; the raw body is
discarded afterwards.

The heuristics intentionally combine several weak signals (sender, subject,
body, links, HTML metadata, tracking number formats) instead of trusting a
single keyword.  This keeps marketing mail out while still recognising the
many different templates used by merchants and carriers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from email.utils import parseaddr
from typing import Any, Final

from .const import (
    CARRIER_AMAZON,
    CARRIER_DEUTSCHE_POST,
    CARRIER_DHL,
    CARRIER_DPD,
    CARRIER_FEDEX,
    CARRIER_GLS,
    CARRIER_HERMES,
    CARRIER_UPS,
    STATUS_CANCELLED,
    STATUS_DELAYED,
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_ORDERED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_READY_FOR_PICKUP,
    STATUS_RETURNED,
    STATUS_SHIPPED,
)
from .util import (
    build_tracking_url,
    clean_whitespace,
    extract_html_details,
    find_expected_delivery,
    find_time_window,
    html_to_text,
    is_http_url,
    local_date,
    normalize_key,
    normalize_tracking,
    truncate,
)

# ---------------------------------------------------------------------------
# Input / output
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EmailMessage:
    """A decoded Gmail message (kept in memory only)."""

    id: str
    thread_id: str | None
    received_at: datetime
    sender_name: str
    sender_email: str
    subject: str
    text: str
    html: str
    snippet: str = ""

    @property
    def sender_domain(self) -> str:
        if "@" not in self.sender_email:
            return ""
        return self.sender_email.rsplit("@", 1)[1].lower().strip(".")

    @property
    def sender_address(self) -> str:
        return self.sender_email.lower()


@dataclass(slots=True)
class ParsedEmail:
    """The compact, persistable facts extracted from one e-mail."""

    message_id: str
    thread_id: str | None
    received_at: str
    kind: str
    status: str | None
    confidence: float
    subject: str
    sender: str
    sender_email: str
    merchant: str | None = None
    carrier: str | None = None
    tracking_numbers: list[str] = field(default_factory=list)
    order_numbers: list[str] = field(default_factory=list)
    product_names: list[str] = field(default_factory=list)
    product_image: str | None = None
    tracking_url: str | None = None
    expected_delivery: str | None = None
    delivery_window: str | None = None
    ordered_at: str | None = None
    shipped_at: str | None = None
    delivered_at: str | None = None
    notes: str | None = None

    def event_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "kind": self.kind,
            "status": self.status,
            "merchant": self.merchant,
            "carrier": self.carrier,
            "tracking_numbers": self.tracking_numbers,
            "order_numbers": self.order_numbers,
            "product_names": self.product_names,
            "expected_delivery": self.expected_delivery,
        }


# ---------------------------------------------------------------------------
# Merchant / carrier knowledge
# ---------------------------------------------------------------------------

MERCHANT_DOMAINS: Final[dict[str, str]] = {
    "amazon.de": "Amazon",
    "amazon.com": "Amazon",
    "amazon.co.uk": "Amazon",
    "amazon.fr": "Amazon",
    "amazon.it": "Amazon",
    "amazon.es": "Amazon",
    "zalando.de": "Zalando",
    "zalando.com": "Zalando",
    "otto.de": "OTTO",
    "otto.com": "OTTO",
    "mediamarkt.de": "MediaMarkt",
    "mediamarkt.at": "MediaMarkt",
    "saturn.de": "SATURN",
    "notebooksbilliger.de": "notebooksbilliger.de",
    "cyberport.de": "Cyberport",
    "alternate.de": "ALTERNATE",
    "mindfactory.de": "Mindfactory",
    "caseking.de": "Caseking",
    "apple.com": "Apple",
    "ebay.de": "eBay",
    "ebay.com": "eBay",
    "ikea.com": "IKEA",
    "ikea.de": "IKEA",
    "hornbach.de": "Hornbach",
    "bauhaus.info": "BAUHAUS",
    "thalia.de": "Thalia",
    "rebuy.de": "reBuy",
    "galaxus.de": "Galaxus",
    "galaxus.ch": "Galaxus",
    "digitec.ch": "Digitec",
    "aliexpress.com": "AliExpress",
    "shein.com": "SHEIN",
    "shein.de": "SHEIN",
    "hm.com": "H&M",
    "zara.com": "Zara",
    "lidl.de": "Lidl",
    "aldi.de": "ALDI",
    "aldi-sued.de": "ALDI SÜD",
    "aldi-nord.de": "ALDI Nord",
    "rossmann.de": "ROSSMANN",
    "douglas.de": "Douglas",
    "samsung.com": "Samsung",
    "lenovo.com": "Lenovo",
    "hp.com": "HP",
    "dell.com": "Dell",
    "logitech.com": "Logitech",
    "sony.de": "Sony",
    "sony.com": "Sony",
    "microsoft.com": "Microsoft",
    "store.google.com": "Google Store",
    "google.com": "Google",
    "conrad.de": "Conrad",
    "pearl.de": "PEARL",
    "voelkner.de": "Voelkner",
    "reichelt.de": "Reichelt",
    "jacob.de": "Jacob",
    "gravis.de": "Gravis",
    "backmarket.de": "Back Market",
    "refurbed.de": "refurbed",
    "ceconomy.de": "MediaMarkt",
    "check24.de": "CHECK24",
    "zooplus.de": "zooplus",
    "fressnapf.de": "Fressnapf",
    "decathlon.de": "Decathlon",
    "adidas.de": "adidas",
    "nike.com": "Nike",
    "aboutyou.de": "ABOUT YOU",
    "bonprix.de": "bonprix",
    "emp.de": "EMP",
    "mymuesli.com": "mymuesli",
    "hellofresh.de": "HelloFresh",
    "wayfair.de": "Wayfair",
    "westwing.de": "Westwing",
    "made.com": "MADE.com",
    "depot-online.com": "Depot",
    "manufactum.de": "Manufactum",
}

MERCHANT_ALIASES: Final[dict[str, str]] = {
    "amazon": "Amazon",
    "amazon de": "Amazon",
    "amazon com": "Amazon",
    "otto": "OTTO",
    "zalando": "Zalando",
    "mediamarkt": "MediaMarkt",
    "media markt": "MediaMarkt",
    "saturn": "SATURN",
    "ikea": "IKEA",
    "ebay": "eBay",
    "lidl": "Lidl",
    "aldi": "ALDI",
    "rossmann": "ROSSMANN",
    "douglas": "Douglas",
    "samsung": "Samsung",
    "lenovo": "Lenovo",
    "logitech": "Logitech",
    "apple": "Apple",
    "microsoft": "Microsoft",
    "google store": "Google Store",
    "rewe": "REWE",
    "edeka": "EDEKA",
}

# Canonical names used for scanning bodies when the sender is a carrier.
_KNOWN_MERCHANT_NAMES: Final[tuple[tuple[str, str], ...]] = tuple(
    sorted(
        {
            name: name
            for name in list(MERCHANT_DOMAINS.values()) + list(MERCHANT_ALIASES.values())
        }.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

CARRIER_DOMAINS: Final[dict[str, str]] = {
    "dhl.de": CARRIER_DHL,
    "dhl.com": CARRIER_DHL,
    "dhl-communication.com": CARRIER_DHL,
    "dhl-news.de": CARRIER_DHL,
    "deutschepost.de": CARRIER_DEUTSCHE_POST,
    "deutsche-post.de": CARRIER_DEUTSCHE_POST,
    "myhermes.de": CARRIER_HERMES,
    "hermesworld.com": CARRIER_HERMES,
    "hermes-europe.de": CARRIER_HERMES,
    "dpd.de": CARRIER_DPD,
    "dpd.com": CARRIER_DPD,
    "gls-group.eu": CARRIER_GLS,
    "gls-group.com": CARRIER_GLS,
    "gls-germany.com": CARRIER_GLS,
    "ups.com": CARRIER_UPS,
    "ups.de": CARRIER_UPS,
    "fedex.com": CARRIER_FEDEX,
    "fedex.de": CARRIER_FEDEX,
    "amazon-logistics.de": CARRIER_AMAZON,
}

_CARRIER_NAME_SCAN: Final[tuple[tuple[str, str], ...]] = (
    ("amazon logistics", CARRIER_AMAZON),
    ("versand durch amazon", CARRIER_AMAZON),
    ("deutsche post", CARRIER_DEUTSCHE_POST),
    ("dhl", CARRIER_DHL),
    ("hermes", CARRIER_HERMES),
    ("dpd", CARRIER_DPD),
    ("gls", CARRIER_GLS),
    ("ups", CARRIER_UPS),
    ("fedex", CARRIER_FEDEX),
)

_GENERIC_SENDER_WORDS: Final = {
    "service",
    "team",
    "support",
    "info",
    "newsletter",
    "no-reply",
    "noreply",
    "shop",
    "online",
    "versand",
    "bestellung",
    "order",
    "mail",
    "notification",
    "benachrichtigung",
    "customer",
    "kundenservice",
    "gmbh",
    "ag",
    "se",
    "inc",
    "ltd",
    "co",
    "kg",
    "ohg",
}

# ---------------------------------------------------------------------------
# Tracking / order patterns
# ---------------------------------------------------------------------------

_UPS_RE = re.compile(r"\b1Z[0-9A-Z]{16}\b", re.IGNORECASE)
_AMAZON_RE = re.compile(r"\bTBA\d{10,16}\b", re.IGNORECASE)
_JJD_RE = re.compile(r"\bJJD\d{10,20}\b", re.IGNORECASE)
_UPU_RE = re.compile(r"\b[A-Z]{2}\d{9}[A-Z]{2}\b")
_NUMERIC_RE = re.compile(r"(?<![A-Za-z0-9.])(\d{10,22})(?![A-Za-z0-9.])")

_TRACKING_CONTEXT = re.compile(
    r"(sendungsnummer|sendungs-nr|sendungsnr|sendungs-id|sendung|paketnummer|"
    r"paket-nr|paket-id|tracking|trackingnummer|tracking number|tracking-id|"
    r"sendungsverfolgung|sendungsinformation|parcel number|parcel id|"
    r"tracking code|verfolgungsnummer|shipment|delivery number)",
    re.IGNORECASE,
)
_TRACKING_LINK_CONTEXT = re.compile(
    r"(track|sendung|paket|parcel|shipment|piececode|tracknum|form_pin|match=|"
    r"sendungsverfolgung|verfolgen)",
    re.IGNORECASE,
)
_ORDER_CONTEXT = re.compile(
    r"(bestellnummer|bestell-nr|bestellnr|bestellungsnummer|bestellung nr|"
    r"bestellung #|order number|order no|order id|order #|auftragsnummer|"
    r"auftragsnr|kundennummer|customer number|invoice|rechnung)",
    re.IGNORECASE,
)
_NEGATIVE_DELIVERY = re.compile(
    r"(nicht zugestellt|konnte nicht zugestellt|konnten nicht zugestellt|"
    r"zustellung nicht möglich|zustellung nicht moeglich|nicht angetroffen|"
    r"empfänger nicht angetroffen|empfaenger nicht angetroffen|"
    r"not delivered|could not be delivered|delivery was not possible)",
    re.IGNORECASE,
)
_FUTURE_DELIVERY = re.compile(
    r"((?:wird|soll|sollte|voraussichtlich|will be|expected to be|planned to be)"
    r".{0,45}(?:zugestellt|geliefert|delivered)|"
    r"(?:zustellung|lieferung|delivery)\s+(?:erfolgt|findet|is expected)"
    r".{0,20}(?:heute|morgen|am|on|between)?|"
    r"(?:kommt|arrives|arriving)\s+(?:heute|morgen|am|on|between))",
    re.IGNORECASE,
)
_STRONG_DELIVERED = re.compile(
    r"(wurde zugestellt|erfolgreich zugestellt|ist zugestellt|"
    r"has been delivered|was delivered|wurde abgegeben|"
    r"in den briefkasten|beim nachbarn|an einen nachbarn|wurde abgelegt)",
    re.IGNORECASE,
)
_ACTUAL_RETURN = re.compile(
    r"(zurückgeschickt|zurueckgeschickt|zurückgesandt|zurueckgesandt|"
    r"retourniert|returned to sender|return to sender|"
    r"rücksendung erhalten|ruecksendung erhalten)",
    re.IGNORECASE,
)

_NON_PACKAGE_SUBJECT = re.compile(
    r"(bewert|bewerte|bewertung|rezension|feedback|umfrage|meinung|erfahrung|"
    r"rechnung|invoice|zahlung|payment|gutschein|coupon|newsletter|angebot|"
    r"rabatt|sale|black friday|cyber monday|deal|empfehlung|entdecke|"
    r"jetzt kaufen|nur heute|werbung)",
    re.IGNORECASE,
)
_NON_PACKAGE_SENDER = re.compile(
    r"^(?:newsletter|marketing|angebote|deals|promo|werbung|bewertung|"
    r"bewerten|review|reviews|feedback|rechnung|invoice|payment|zahlen)",
    re.IGNORECASE,
)

_ORDER_LABEL_RE = re.compile(
    r"(?:bestell(?:nummer|ungsnummer|nr\.?|id)|"
    r"bestellung\s*(?:nr\.?|nummer|#)|"
    r"auftrags(?:nummer|nr\.?)?|order\s*(?:number|no\.?|id|#)|"
    r"kundennummer|customer\s*(?:number|no\.?))\s*[:#\-]?\s*"
    r"([A-Z0-9][A-Z0-9\-\/]{4,30})",
    re.IGNORECASE,
)
_AMAZON_ORDER_RE = re.compile(r"\b\d{3}-\d{7}-\d{7}\b")

_TRACKING_URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Status / kind vocabulary (normalised via normalize_key)
# ---------------------------------------------------------------------------

_DELIVERED_PHRASES: Final = (
    "wurde zugestellt",
    "erfolgreich zugestellt",
    "ist zugestellt",
    "zugestellt",
    "wurde abgegeben",
    "in den briefkasten",
    "beim nachbarn abgegeben",
    "an einen nachbarn",
    "wurde abgelegt",
    "abgelegt",
    "delivered",
    "has been delivered",
    "was delivered",
    "left with",
)
_DELAY_PHRASES: Final = (
    "verzoegert",
    "verspaetet",
    "verzoegerung",
    "verspaetung",
    "delay",
    "delayed",
    "konnte nicht zugestellt",
    "zustellung nicht moeglich",
    "nicht angetroffen",
    "empfaenger nicht angetroffen",
    "problem bei der zustellung",
    "spaeter als geplant",
    "wird sich verzoegern",
    "es kommt zu verzoegerungen",
    "delivery exception",
    "exception",
)
_PICKUP_PHRASES: Final = (
    "abholbereit",
    "zur abholung bereit",
    "kann abgeholt werden",
    "kannst du abholen",
    "liegt zur abholung",
    "zur abholung",
    "abholung in der packstation",
    "abholung in der filiale",
    "in der packstation abholen",
    "in der postfiliale abholen",
    "liegt in der packstation",
    "liegt in der postfiliale",
    "abholfach",
    "post office",
    "ready for pickup",
    "awaiting pickup",
    "collection point",
    "retail outlet",
    "abholschein",
)
_OUT_PHRASES: Final = (
    "in zustellung",
    "ist in zustellung",
    "befindet sich in zustellung",
    "wird heute zugestellt",
    "zustellung erfolgt heute",
    "wird dir heute zugestellt",
    "wird ihnen heute zugestellt",
    "wird zugestellt",
    "soll zugestellt werden",
    "zustellung am",
    "wird geliefert",
    "soll geliefert werden",
    "out for delivery",
    "beim zusteller",
    "mit dem zusteller",
    "zustellfahrzeug",
    "kommt heute",
    "delivery today",
    "delivery expected",
    "arriving",
)
_SHIPPED_PHRASES: Final = (
    "wurde versendet",
    "wurde verschickt",
    "ist versandt",
    "wurde versandt",
    "ist unterwegs",
    "auf dem weg",
    "shipped",
    "has been shipped",
    "dispatched",
    "wurde abgeholt",
    "uebergeben an",
    "in bearbeitung beim versand",
    "bereit zum versand",
)
_TRANSIT_PHRASES: Final = (
    "im paketzentrum",
    "paketzentrum",
    "im transport",
    "in transit",
    "unterwegs",
    "angekommen",
    "sortiert",
    "verladen",
    "transportiert",
    "im zielpaketzentrum",
    "in der region",
    "auf dem weg",
)
_ORDERED_PHRASES: Final = (
    "bestellbestaetigung",
    "bestellbestaetigung",
    "bestellung eingegangen",
    "bestellung erhalten",
    "wir haben deine bestellung erhalten",
    "wir haben ihre bestellung erhalten",
    "danke fuer deine bestellung",
    "danke fuer ihre bestellung",
    "vielen dank fuer ihre bestellung",
    "vielen dank fuer deine bestellung",
    "order confirmation",
    "thank you for your order",
    "thanks for your order",
    "bestellung wurde aufgegeben",
    "deine bestellung ist eingegangen",
)
_RETURN_LABEL_PHRASES: Final = (
    "retourenlabel",
    "ruecksendelabel",
    "ruecksende label",
    "return label",
    "retourenschein",
    "ruecksendeschein",
    "retoure anmelden",
)
_RETURN_PHRASES: Final = (
    "retoure",
    "ruecksendung",
    "zurueckgesandt",
    "zurueckgeschickt",
    "zurueckgesendet",
    "returned to sender",
    "return to sender",
    "wurde zurueckgeschickt",
    "retourniert",
    "rueckgabe",
    "rueckabwicklung",
)
_CANCEL_PHRASES: Final = (
    "storniert",
    "stornierung",
    "wurde storniert",
    "bestellung storniert",
    "cancelled",
    "canceled",
    "order cancelled",
    "order canceled",
)

_PRODUCT_LABEL_RE = re.compile(
    r"(?:artikel|produkt|position|bestellt|versandt|geliefert|item|product)"
    r"\s*[:\-]\s*(.{6,180})",
    re.IGNORECASE,
)
_PRODUCT_QUANTITY_RE = re.compile(
    r"^\s*(?:(\d{1,3})\s*[x×]\s*|[x×]\s*(\d{1,3})\s+)(.{6,180})$",
    re.IGNORECASE,
)
_PRODUCT_SUBJECT_PATTERNS: Final = (
    re.compile(
        r"(?:paket|sendung|bestellung)\s+(?:mit|für|fuer)\s+[\"„“'‚‘]?"
        r"(.{6,140}?)[\"“”'‘’]?\s+(?:wurde|ist|wird|kommt)",
        re.IGNORECASE,
    ),
    re.compile(r"versandbest(?:ä|ae)tigung\s+(?:für|fuer)\s+(.{6,140})", re.IGNORECASE),
    re.compile(r"(?:ihre|deine|your)\s+bestellung\s*[:\-]\s*(.{6,140})", re.IGNORECASE),
    re.compile(r"(?:order|bestellung)\s*[#:]?\s*[\w-]+\s*[:\-]\s*(.{6,140})", re.IGNORECASE),
)

_PRODUCT_REJECT_RAW = {
    "bestellung",
    "bestellbestaetigung",
    "bestellbestätigung",
    "sendung",
    "sendungsverfolgung",
    "paket",
    "pakete",
    "lieferung",
    "versand",
    "versandbestaetigung",
    "versandbestätigung",
    "rechnung",
    "retoure",
    "ruecksendung",
    "rücksendung",
    "kundenkonto",
    "agb",
    "impressum",
    "datenschutz",
    "hilfe",
    "support",
    "kontakt",
    "mehr erfahren",
    "jetzt entdecken",
    "jetzt kaufen",
    "zum shop",
    "alle angebote",
    "angebot",
    "newsletter",
    "gutschein",
    "warenkorb",
    "zur bestellung",
    "bestellstatus",
    "sendungsdetails",
    "tracking",
    "details ansehen",
    "jetzt ansehen",
    "hier klicken",
    "klicken sie hier",
    "unsubscribe",
    "abmelden",
    "deine bestellung",
    "ihre bestellung",
    "dein paket",
    "ihr paket",
    "deine sendung",
    "ihre sendung",
    "sendung verfolgen",
    "paket verfolgen",
    "lieferung verfolgen",
    "sendungsstatus",
    "status ansehen",
    "tracking anzeigen",
    "meine bestellungen",
    "alle bestellungen",
    "bestellübersicht",
    "bestelluebersicht",
    "bestellhistorie",
    "mein konto",
    "anmelden",
    "registrieren",
    "jetzt bewerten",
    "bewerten",
    "rezension schreiben",
    "produkt bewerten",
    "ruecksendung starten",
    "rücksendung starten",
    "retoure anmelden",
    "problem melden",
    "kundenservice",
    "hilfe center",
    "zur startseite",
    "weiter einkaufen",
    "shop besuchen",
    "cookie",
    "einstellungen",
    "amazon de",
    "amazon",
    "dhl",
    "hermes",
    "dpd",
    "gls",
    "ups",
    "fedex",
}
_PRODUCT_REJECT_KEYS: Final = frozenset(
    normalize_key(item) for item in _PRODUCT_REJECT_RAW
)

_IMAGE_REJECT = re.compile(
    r"(pixel|beacon|track(?:ing)?|spacer|transparent|logo|icon|sprite|badge|"
    r"flag|avatar|newsletter|header|footer|banner|1x1|blank|open\.gif|"
    r"spacer\.gif|facebook|twitter|instagram|youtube|linkedin)",
    re.IGNORECASE,
)
_IMAGE_PRODUCT_HOST = re.compile(
    r"(media-amazon|ssl-images-amazon|images-amazon|media\.amazon|"
    r"images\.otto|image\.zalando|media\.mediamarkt|media\.saturn|"
    r"images\.ikea|scene7|cloudinary|shopify|cdn\.shopify)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_phrase(haystack: str, phrase: str) -> bool:
    return normalize_key(phrase) in haystack


def _score_phrases(haystack: str, subject: str, phrases: tuple[str, ...]) -> int:
    score = 0
    for phrase in phrases:
        key = normalize_key(phrase)
        if not key:
            continue
        if key in haystack:
            score += 2 + min(len(key) // 18, 2)
        if key in subject:
            score += 2
    return score


def _merchant_from_domain(domain: str) -> str | None:
    domain = domain.lower().strip(".")
    if not domain:
        return None
    for merchant_domain, name in MERCHANT_DOMAINS.items():
        if domain == merchant_domain or domain.endswith(f".{merchant_domain}"):
            return name
    return None


def _carrier_from_domain(domain: str) -> str | None:
    domain = domain.lower().strip(".")
    for carrier_domain, carrier in CARRIER_DOMAINS.items():
        if domain == carrier_domain or domain.endswith(f".{carrier_domain}"):
            return carrier
    return None


def _clean_sender_name(name: str) -> str | None:
    name = clean_whitespace(name).strip(" \"'")
    if not name:
        return None
    name = re.split(r"\s+(?:via|über|ueber)\s+", name, flags=re.IGNORECASE)[0]
    name = re.split(r"\s*[|–—]\s*", name)[0]
    words = [word for word in name.split() if word.casefold() not in _GENERIC_SENDER_WORDS]
    name = " ".join(words).strip(" -,.")
    if not name or len(name) < 2 or len(name) > 40:
        return None
    if any(word.casefold() in _GENERIC_SENDER_WORDS for word in name.split()):
        return None
    return name


def _merchant_from_text(text: str, subject: str) -> str | None:
    subject_key = normalize_key(subject)
    text_key = normalize_key(text)
    # Explicit seller lines are the most reliable fallback.
    for pattern in (
        (r"(?:verk(?:ä|ae)ufer|seller|versand durch|im auftrag von|bestellung bei|"
        r"shop)\s*[:\-]\s*([^\n]{2,60})"),
    ):
        match = re.search(pattern, f"{subject}\n{text}", re.IGNORECASE)
        if match:
            candidate = _clean_sender_name(match.group(1))
            if candidate:
                canonical = MERCHANT_ALIASES.get(normalize_key(candidate))
                return canonical or candidate

    for name, canonical in _KNOWN_MERCHANT_NAMES:
        key = normalize_key(name)
        if len(key) < 3:
            continue
        if re.search(rf"\b{re.escape(key)}\b", subject_key):
            return canonical
    for name, canonical in _KNOWN_MERCHANT_NAMES:
        key = normalize_key(name)
        if len(key) < 3:
            continue
        if re.search(rf"\b{re.escape(key)}\b", text_key):
            return canonical
    return None


def _infer_carrier_from_tracking(tracking: str) -> str | None:
    value = normalize_tracking(tracking)
    if value.startswith("1Z") and len(value) == 18:
        return CARRIER_UPS
    if value.startswith("TBA"):
        return CARRIER_AMAZON
    if value.startswith("JJD"):
        return CARRIER_DHL
    if re.fullmatch(r"[A-Z]{2}\d{9}[A-Z]{2}", value):
        # UPU codes ending in DE are used by both DHL and Deutsche Post.
        # Let the sender domain / wording decide instead of guessing.
        return None
    if len(value) == 20 and value.startswith("00340"):
        return CARRIER_DHL
    if len(value) == 14:
        return None  # DPD, Hermes and GLS all use 14 digit numbers
    return None


def _carrier_fits(carrier: str | None, tracking: str) -> bool:
    value = normalize_tracking(tracking)
    if not carrier:
        return True
    if carrier == CARRIER_UPS:
        return value.startswith("1Z") or len(value) in (12, 18)
    if carrier == CARRIER_AMAZON:
        return value.startswith("TBA") or len(value) in (12, 14, 15)
    if carrier == CARRIER_DHL:
        return value.startswith(("JJD", "00340")) or 10 <= len(value) <= 20
    if carrier == CARRIER_DPD:
        return len(value) in (14, 28)
    if carrier == CARRIER_HERMES:
        return 12 <= len(value) <= 20
    if carrier == CARRIER_GLS:
        return 8 <= len(value) <= 20
    if carrier == CARRIER_FEDEX:
        return len(value) in (12, 15, 20, 22)
    if carrier == CARRIER_DEUTSCHE_POST:
        return 10 <= len(value) <= 20
    return True


def _detect_carrier(
    domain: str,
    sender_name: str,
    subject: str,
    text: str,
    tracking_numbers: list[str],
) -> str | None:
    scores: dict[str, int] = {}

    def add(carrier: str | None, points: int) -> None:
        if carrier:
            scores[carrier] = scores.get(carrier, 0) + points

    add(_carrier_from_domain(domain), 6)
    lower_domain = domain.casefold()
    if "amazon" in lower_domain and any(
        token in text.casefold() for token in ("amazon logistics", "versand durch amazon")
    ):
        add(CARRIER_AMAZON, 5)

    haystack = f"{sender_name}\n{subject}\n{text}".casefold()
    for name, carrier in _CARRIER_NAME_SCAN:
        if re.search(rf"\b{re.escape(name)}\b", haystack):
            add(carrier, 3 if name in subject.casefold() else 1)

    for tracking in tracking_numbers:
        inferred = _infer_carrier_from_tracking(tracking)
        # A carrier-specific tracking format is stronger evidence than any
        # marketing wording such as "Versand durch Amazon".
        add(inferred, 8)
        value = normalize_tracking(tracking)
        if value.startswith("TBA"):
            add(CARRIER_AMAZON, 4)
        if value.startswith("1Z"):
            add(CARRIER_UPS, 4)
        if value.startswith("JJD"):
            add(CARRIER_DHL, 4)

    # Amazon is a merchant, not automatically Amazon Logistics.  Only count
    # the Amazon carrier when a TBA number or explicit wording is present.
    if CARRIER_AMAZON in scores and not any(
        normalize_tracking(number).startswith("TBA") for number in tracking_numbers
    ) and not any(
        token in haystack for token in ("amazon logistics", "versand durch amazon")
    ):
        scores.pop(CARRIER_AMAZON, None)

    if not scores:
        return None
    return max(scores, key=lambda carrier: scores[carrier])


def _extract_order_numbers(text: str, subject: str, tracking_numbers: list[str]) -> list[str]:
    combined = f"{subject}\n{text}"
    numbers: list[str] = []
    tracking_keys = {normalize_tracking(number) for number in tracking_numbers}

    for match in _AMAZON_ORDER_RE.finditer(combined):
        numbers.append(match.group(0))

    for match in _ORDER_LABEL_RE.finditer(combined):
        candidate = match.group(1).strip(" .,:;-")
        if len(candidate) < 5 or not re.search(r"\d", candidate):
            continue
        if normalize_tracking(candidate) in tracking_keys:
            continue
        # A label followed by a date is not an order number.
        if re.fullmatch(r"\d{1,2}\.?\d{0,2}\.?\d{2,4}", candidate):
            continue
        numbers.append(candidate)

    unique: list[str] = []
    seen: set[str] = set()
    for number in numbers:
        key = number.upper().replace(" ", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(number)
    return unique[:3]


def _extract_tracking_numbers(
    text: str,
    subject: str,
    links: list[tuple[str, str]],
) -> list[str]:
    combined = f"{subject}\n{text}"
    candidates: list[tuple[str, int, str]] = []  # value, weight, source

    for pattern, weight in (
        (_UPS_RE, 8),
        (_AMAZON_RE, 8),
        (_JJD_RE, 7),
        (_UPU_RE, 7),
    ):
        for match in pattern.finditer(combined):
            candidates.append((match.group(0), weight, "pattern"))

    for match in _NUMERIC_RE.finditer(combined):
        value = match.group(1)
        before = combined[max(0, match.start() - 100) : match.start()]
        after = combined[match.end() : match.end() + 50]
        context = f"{before}{after}"
        has_tracking_context = bool(_TRACKING_CONTEXT.search(context))
        has_order_context = bool(_ORDER_CONTEXT.search(context))
        is_link_number = any(value in href for href, _text in links)
        if not has_tracking_context and not is_link_number:
            continue
        if has_order_context and not has_tracking_context:
            continue
        if len(set(value)) == 1:
            continue
        candidates.append((value, 5 if has_tracking_context else 3, "number"))

    # Tracking numbers embedded in tracking links are often the only place a
    # number appears in HTML only mails.
    for href, _link_text in links:
        if not _TRACKING_LINK_CONTEXT.search(href):
            continue
        for match in _NUMERIC_RE.finditer(href):
            candidates.append((match.group(1), 4, "link"))
        for pattern in (_UPS_RE, _AMAZON_RE, _JJD_RE, _UPU_RE):
            for match in pattern.finditer(href):
                candidates.append((match.group(0), 7, "link"))

    # Prefer longer, strong candidates and remove duplicates.
    candidates.sort(key=lambda item: item[1], reverse=True)
    result: list[str] = []
    seen: set[str] = set()
    for value, _weight, _source in candidates:
        key = normalize_tracking(value)
        if len(key) < 8 or key in seen:
            continue
        # Do not accept a number that is also reported as the order number
        # unless it has a strong carrier-specific format.
        seen.add(key)
        result.append(value.upper() if any(char.isalpha() for char in value) else value)
        if len(result) >= 3:
            break
    return result


def _extract_tracking_url(
    links: list[tuple[str, str]],
    text: str,
    carrier: str | None,
    tracking_numbers: list[str],
) -> str | None:
    tracking_keys = {normalize_tracking(number) for number in tracking_numbers}
    best: tuple[int, str] | None = None

    all_links = [(href, text) for href, text in links]
    all_links.extend((url, "") for url in _TRACKING_URL_RE.findall(text))

    for href, link_text in all_links:
        if not is_http_url(href):
            continue
        href_key = href.upper()
        score = 0
        if any(key and key in href_key for key in tracking_keys):
            score += 6
        if _TRACKING_LINK_CONTEXT.search(href) or _TRACKING_LINK_CONTEXT.search(link_text):
            score += 3
        href_host = href.split("/")[2] if href.count("/") >= 2 else ""
        if _carrier_from_domain(href_host):
            score += 2
        if carrier and carrier in href.casefold():
            score += 2
        if "unsubscribe" in href.casefold() or "abmelden" in href.casefold():
            score -= 10
        if score >= 5 and (best is None or score > best[0]):
            best = (score, href)

    if best:
        return best[1]
    if tracking_numbers:
        return build_tracking_url(carrier, tracking_numbers[0])
    return None


def _clean_product(value: str) -> str | None:
    value = html_to_text(value) if "<" in value else value
    value = clean_whitespace(value)
    value = value.strip(" \"'„“”‚‘’–—-:;,.|")
    value = re.sub(r"^(?:\d{1,3}\s*[x×]\s*|[x×]\s*\d{1,3}\s+)", "", value).strip()
    value = re.sub(r"\s+\d+[,.]\d{2}\s*€.*$", "", value).strip()
    value = re.sub(r"\s+(?:zzgl\.|inkl\.).*$", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+-\s+(?:Amazon|DHL|Hermes|DPD|GLS|UPS|FedEx).*$", "", value).strip()
    if not value:
        return None
    if len(value) < 6 or len(value) > 160:
        return None
    if len(value.split()) > 16:
        return None
    key = normalize_key(value)
    if not key or key in _PRODUCT_REJECT_KEYS:
        return None
    if any(
        token in key
        for token in (
            "agb",
            "impressum",
            "datenschutz",
            "newsletter",
            "unsubscribe",
            "abmelden",
            "warenkorb",
            "gutschein",
            "jetzt kaufen",
            "mehr erfahren",
            "alle angebote",
            "kundenkonto",
            "bestellstatus",
            "sendungsverfolgung",
        )
    ):
        return None
    if re.search(r"(?:https?://|www\.|@)", value, re.IGNORECASE):
        return None
    if re.fullmatch(r"[\d\s.,€%/:–-]+", value):
        return None
    if re.fullmatch(r"(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag).*", key):
        return None
    if re.fullmatch(r"(?:januar|februar|maerz|april|mai|juni|juli|august|september|oktober|november|dezember).*", key):
        return None
    return truncate(value, 160)


def _extract_products(
    text: str,
    subject: str,
    links: list[tuple[str, str]],
    images: list[dict[str, str]],
    merchant: str | None,
    carrier: str | None,
) -> list[str]:
    candidates: list[tuple[int, str]] = []

    for pattern in _PRODUCT_SUBJECT_PATTERNS:
        for match in pattern.finditer(subject):
            clean = _clean_product(match.group(1))
            if clean:
                candidates.append((10, clean))

    for href, link_text in links:
        clean = _clean_product(link_text)
        if not clean:
            continue
        score = 3
        href_lower = href.casefold()
        if re.search(r"/(?:dp|gp/product)/[A-Z0-9]{10}", href, re.IGNORECASE):
            score += 7
        elif any(token in href_lower for token in ("/product", "/artikel", "/p/", "/shop/")):
            score += 2
        if clean.casefold() in (merchant or "").casefold():
            continue
        candidates.append((score, clean))

    for image in images:
        clean = _clean_product(image.get("alt", ""))
        if clean:
            candidates.append((4, clean))

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = _PRODUCT_LABEL_RE.search(line)
        if match:
            clean = _clean_product(match.group(1))
            if clean:
                candidates.append((7, clean))
        match = _PRODUCT_QUANTITY_RE.match(line)
        if match:
            clean = _clean_product(match.group(3))
            if clean:
                candidates.append((5, clean))

    # Product lines often follow a heading such as "Artikel" on its own line.
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(r"(?:artikel|produkte?|position|items?|produkt)", line, re.IGNORECASE):
            clean = _clean_product(lines[index + 1])
            if clean:
                candidates.append((6, clean))

    if merchant:
        merchant_key = normalize_key(merchant)
        candidates = [
            (score, value)
            for score, value in candidates
            if normalize_key(value) != merchant_key
        ]
    if carrier:
        carrier_keys = {normalize_key(carrier), normalize_key({"dhl": "DHL"}.get(carrier, carrier))}
        candidates = [
            (score, value)
            for score, value in candidates
            if normalize_key(value) not in carrier_keys
        ]

    scored: list[tuple[float, str]] = []
    for base_score, value in candidates:
        key = normalize_key(value)
        if not key:
            continue
        score = float(base_score)
        word_count = len(value.split())
        if 2 <= word_count <= 10:
            score += 2
        if 12 <= len(value) <= 90:
            score += 1
        # Prefer values with a model number or brand-like capitalisation.
        if re.search(r"\d", value):
            score += 0.5
        scored.append((score, value))

    scored.sort(key=lambda item: item[0], reverse=True)
    result: list[str] = []
    seen: set[str] = set()
    for _score, value in scored:
        key = normalize_key(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= 5:
            break
    return result


def _extract_product_image(
    meta: dict[str, str],
    images: list[dict[str, str]],
    links: list[tuple[str, str]],
    product_names: list[str],
) -> str | None:
    candidates: list[tuple[int, str]] = []
    for name in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
        value = meta.get(name)
        if value and not _IMAGE_REJECT.search(value):
            candidates.append((8, value))

    product_keys = [normalize_key(name) for name in product_names[:3]]
    base_url = links[0][0] if links else None
    for image in images:
        src = image.get("src", "")
        if not src or src.startswith("data:"):
            continue
        alt = image.get("alt", "")
        score = 0
        if _IMAGE_PRODUCT_HOST.search(src):
            score += 6
        if "/images/I/" in src:
            score += 5
        if re.search(r"\.(?:jpe?g|png|webp)(?:\?|$)", src, re.IGNORECASE):
            score += 2
        if _IMAGE_REJECT.search(src) or _IMAGE_REJECT.search(alt):
            score -= 15
        width = image.get("width", "")
        height = image.get("height", "")
        try:
            if width and int(re.sub(r"\D", "", width) or 0) <= 2:
                score -= 10
            if height and int(re.sub(r"\D", "", height) or 0) <= 2:
                score -= 10
            if width and int(re.sub(r"\D", "", width) or 0) >= 100:
                score += 2
        except ValueError:
            pass
        alt_key = normalize_key(alt)
        if alt_key and any(key and (key in alt_key or alt_key in key) for key in product_keys):
            score += 5
        if score >= 5:
            candidates.append((score, src))

    candidates.sort(key=lambda item: item[0], reverse=True)
    for _score, src in candidates:
        url = src
        if src.startswith("//"):
            url = f"https:{src}"
        elif src.startswith("/") and base_url:
            from urllib.parse import urlparse

            parsed = urlparse(base_url)
            url = f"{parsed.scheme}://{parsed.netloc}{src}"
        if is_http_url(url):
            return truncate(url, 2000)
    return None


def _detect_status(
    text: str,
    subject: str,
) -> tuple[str, str | None, float, str | None]:
    haystack = normalize_key(f"{subject}\n{text}")
    subject_key = normalize_key(subject)
    negative = bool(_NEGATIVE_DELIVERY.search(f"{subject}\n{text}"))

    scores = {
        "delivered": _score_phrases(haystack, subject_key, _DELIVERED_PHRASES),
        "delay": _score_phrases(haystack, subject_key, _DELAY_PHRASES),
        "pickup": _score_phrases(haystack, subject_key, _PICKUP_PHRASES),
        "out_for_delivery": _score_phrases(haystack, subject_key, _OUT_PHRASES),
        "shipped": _score_phrases(haystack, subject_key, _SHIPPED_PHRASES),
        "in_transit": _score_phrases(haystack, subject_key, _TRANSIT_PHRASES),
        "ordered": _score_phrases(haystack, subject_key, _ORDERED_PHRASES),
        "returned": _score_phrases(haystack, subject_key, _RETURN_PHRASES),
        "cancelled": _score_phrases(haystack, subject_key, _CANCEL_PHRASES),
        "return_label": _score_phrases(haystack, subject_key, _RETURN_LABEL_PHRASES),
    }

    if negative and scores["delay"] == 0:
        scores["delay"] = 3
    if negative:
        scores["delivered"] = 0

    combined_text = f"{subject}\n{text}"
    if _FUTURE_DELIVERY.search(combined_text) and not _STRONG_DELIVERED.search(combined_text):
        scores["delivered"] = 0
        # "wird am 29.11. zugestellt" has the date between the auxiliary
        # verb and "zugestellt", so the fixed phrases above do not match.
        scores["out_for_delivery"] = max(scores["out_for_delivery"], 3)

    # "Retourenlabel" is not a returned parcel; do not let the word "retoure"
    # in the label e-mail mark an existing shipment as returned.
    if scores["return_label"] > 0 and not _ACTUAL_RETURN.search(combined_text):
        return "return_label", None, 0.55, "Return label received"

    # Explicit carrier/label wording should not masquerade as a delivered
    # parcel just because a footer contains "zugestellt".
    if scores["delivered"] and scores["delay"] > scores["delivered"]:
        scores["delivered"] = 0

    priority = {
        "returned": 7,
        "cancelled": 6,
        "delivered": 5,
        "pickup": 4,
        "out_for_delivery": 3,
        "delay": 2,
        "shipped": 1,
        "in_transit": 1,
        "ordered": 0,
    }
    best = max(
        scores,
        key=lambda kind: (
            scores[kind],
            priority.get(kind, 0),
            kind in subject_key,
        ),
    )
    best_score = scores[best]
    if best_score <= 0:
        return "unknown", None, 0.0, None

    status_map = {
        "delivered": STATUS_DELIVERED,
        "delay": STATUS_DELAYED,
        "pickup": STATUS_READY_FOR_PICKUP,
        "out_for_delivery": STATUS_OUT_FOR_DELIVERY,
        "shipped": STATUS_SHIPPED,
        "in_transit": STATUS_IN_TRANSIT,
        "ordered": STATUS_ORDERED,
        "returned": STATUS_RETURNED,
        "cancelled": STATUS_CANCELLED,
    }
    status = status_map.get(best)
    kind = best
    if best == "out_for_delivery":
        kind = "delivery_announcement"
    elif best == "in_transit":
        kind = "tracking_update"
    elif best == "shipped":
        kind = "shipping_confirmation"
    elif best == "ordered":
        kind = "order_confirmation"
    elif best == "delay":
        kind = "delay"
    elif best == "pickup":
        kind = "pickup"
    elif best == "returned":
        kind = "return"
    elif best == "cancelled":
        kind = "cancellation"
    elif best == "delivered":
        kind = "delivered"

    confidence = min(0.98, 0.35 + best_score / 20)
    return kind, status, confidence, STATUS_LABEL_HINTS.get(best)


STATUS_LABEL_HINTS: Final[dict[str, str]] = {
    "delivered": "Delivery confirmed",
    "delay": "Delay reported",
    "pickup": "Pickup required",
    "out_for_delivery": "Out for delivery",
    "shipped": "Shipping confirmation",
    "in_transit": "Tracking update",
    "ordered": "Order confirmation",
    "returned": "Return",
    "cancelled": "Cancellation",
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class EmailParser:
    """Turn a decoded Gmail message into a :class:`ParsedEmail`."""

    def __init__(self, tz: tzinfo) -> None:
        self._tz = tz

    def parse(self, email: EmailMessage) -> ParsedEmail | None:
        return self._parse(email)

    def _parse(self, email: EmailMessage) -> ParsedEmail | None:
        subject = clean_whitespace(email.subject)
        text = email.text or html_to_text(email.html)
        text = clean_whitespace(text)[:200_000]
        html_details = extract_html_details(email.html)
        links = [
            (href, link_text)
            for href, link_text in html_details.get("links", [])
            if isinstance(href, str)
        ]
        images = [
            image for image in html_details.get("images", []) if isinstance(image, dict)
        ]
        meta = {
            str(key): str(value)
            for key, value in dict(html_details.get("meta", {})).items()
        }

        domain = email.sender_domain
        sender_is_carrier = _carrier_from_domain(domain) is not None
        merchant = _merchant_from_domain(domain)
        if merchant is None:
            canonical = MERCHANT_ALIASES.get(normalize_key(email.sender_name))
            if canonical:
                merchant = canonical
        if merchant is None and not sender_is_carrier:
            merchant = _clean_sender_name(email.sender_name)
            if merchant and not any(
                normalize_key(merchant) == normalize_key(name)
                for name in _KNOWN_MERCHANT_NAMES
            ):
                # Only keep a free-form display name if it looks like a shop,
                # not like a person or a generic mailbox.
                if any(
                    token in normalize_key(merchant)
                    for token in ("gmbh", "shop", "store", "versand", "handel", "ag", "se")
                ):
                    pass
                elif len(merchant.split()) > 2:
                    merchant = None
        if merchant is None and sender_is_carrier:
            merchant = _merchant_from_text(text, subject)

        tracking_numbers = _extract_tracking_numbers(text, subject, links)
        # Review requests, invoices, newsletters and discount mails often
        # contain the word "Bestellung" and an order number.  They are not
        # parcels.  A real tracking number overrides this guard.
        sender_local = email.sender_email.split("@", 1)[0]
        if not tracking_numbers and (
            _NON_PACKAGE_SUBJECT.search(subject)
            or _NON_PACKAGE_SENDER.search(sender_local)
        ):
            return None
        order_numbers = _extract_order_numbers(text, subject, tracking_numbers)
        carrier = _detect_carrier(domain, email.sender_name, subject, text, tracking_numbers)

        kind, status, confidence, hint = self._detect_status_for_mail(
            text, subject, tracking_numbers, order_numbers, carrier, merchant
        )
        if kind == "unknown":
            return None

        # Relevance gates.  These keep newsletters and security mails out.
        if kind == "order_confirmation":
            strong_order_phrase = any(
                _has_phrase(normalize_key(f"{subject}\n{text}"), phrase)
                for phrase in (
                    "bestellbestaetigung",
                    "bestellbestätigung",
                    "order confirmation",
                    "wir haben deine bestellung erhalten",
                    "wir haben ihre bestellung erhalten",
                )
            )
            if not order_numbers and not (merchant and strong_order_phrase):
                return None
        elif kind == "shipping_confirmation":
            if not (tracking_numbers or order_numbers or (merchant and carrier)):
                return None
        elif kind in {"delivery_announcement", "tracking_update", "delay", "pickup", "delivered"}:
            # A merchant name alone is not enough for a status mail; that would
            # turn generic Amazon/marketplace newsletters into "delivered"
            # parcels.  Require a tracking number, an order number or a known
            # carrier.
            if not (tracking_numbers or order_numbers or carrier):
                return None
        elif kind in {"return_label", "return", "cancellation"}:
            if not (merchant or order_numbers or tracking_numbers or carrier):
                return None

        product_names = _extract_products(
            text, subject, links, images, merchant, carrier
        )
        product_image = _extract_product_image(meta, images, links, product_names)
        tracking_url = _extract_tracking_url(
            links, text, carrier, tracking_numbers
        )

        local_received = email.received_at.astimezone(self._tz)
        allow_past = status in {STATUS_DELIVERED, STATUS_RETURNED}
        expected = find_expected_delivery(
            text,
            subject,
            local_received,
            allow_past=allow_past,
            require_context=kind not in {"order_confirmation"},
        )
        window = find_time_window(text, subject)
        if window and kind in {"order_confirmation", "return_label", "cancellation"}:
            window = None
        if not expected and kind in {"delivery_announcement", "pickup", "delivered"}:
            if kind == "delivery_announcement" and any(
                _has_phrase(normalize_key(f"{subject}\n{text}"), phrase)
                for phrase in ("heute", "today")
            ):
                expected = local_date(email.received_at, self._tz)
        # An announcement for a future day is not "out for delivery" yet.
        if (
            status == STATUS_OUT_FOR_DELIVERY
            and expected
            and expected > local_date(email.received_at, self._tz)
        ):
            status = STATUS_IN_TRANSIT

        received_iso = email.received_at.isoformat()
        ordered_at = local_date(email.received_at, self._tz) if status == STATUS_ORDERED else None
        shipped_at = (
            local_date(email.received_at, self._tz)
            if status in {STATUS_SHIPPED, STATUS_IN_TRANSIT, STATUS_OUT_FOR_DELIVERY}
            else None
        )
        delivered_at = None
        if status == STATUS_DELIVERED:
            delivered_at = expected or local_date(email.received_at, self._tz)

        notes = truncate(hint, 120)
        return ParsedEmail(
            message_id=email.id,
            thread_id=email.thread_id,
            received_at=received_iso,
            kind=kind,
            status=status,
            confidence=round(confidence, 2),
            subject=truncate(subject, 300) or "",
            sender=domain or truncate(email.sender_name, 80) or "",
            sender_email=email.sender_email,
            merchant=merchant,
            carrier=carrier,
            tracking_numbers=tracking_numbers,
            order_numbers=order_numbers,
            product_names=product_names,
            product_image=product_image,
            tracking_url=tracking_url
            or build_tracking_url(carrier, tracking_numbers[0] if tracking_numbers else None),
            expected_delivery=expected,
            delivery_window=window,
            ordered_at=ordered_at,
            shipped_at=shipped_at,
            delivered_at=delivered_at,
            notes=notes,
        )

    def _detect_status_for_mail(
        self,
        text: str,
        subject: str,
        tracking_numbers: list[str],
        order_numbers: list[str],
        carrier: str | None,
        merchant: str | None,
    ) -> tuple[str, str | None, float, str | None]:
        kind, status, confidence, hint = _detect_status(text, subject)
        if kind != "unknown":
            return kind, status, confidence, hint

        if tracking_numbers:
            return (
                "tracking_update",
                STATUS_IN_TRANSIT,
                0.45,
                "Tracking number detected",
            )
        # A carrier sender alone is not enough: carriers also send marketing.
        return ("unknown", None, 0.0, None)


# ---------------------------------------------------------------------------
# Small helpers used by tests and diagnostics
# ---------------------------------------------------------------------------


def parse_sender(value: str) -> tuple[str, str]:
    name, address = parseaddr(value or "")
    return clean_whitespace(name), address.lower()


def looks_like_tracking_number(value: str) -> bool:
    normalized = normalize_tracking(value)
    return bool(
        _UPS_RE.search(value)
        or _AMAZON_RE.search(value)
        or _JJD_RE.search(value)
        or _UPU_RE.search(value)
        or (10 <= len(normalized) <= 22 and normalized.isdigit())
    )


def detect_carrier(value: str) -> str | None:
    return _detect_carrier("", "", value, "", [])
