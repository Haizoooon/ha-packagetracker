"""Shared parsing, date and text helpers.

Everything here is pure Python (apart from optional Home Assistant date
helpers in the coordinator) and therefore easy to unit test.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime, timedelta, tzinfo
from html import unescape
from html.parser import HTMLParser
from typing import Final
from urllib.parse import urlparse

from .const import CARRIER_NAMES, TRACKING_URL_TEMPLATES

# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def utcnow_iso() -> str:
    return to_iso(utcnow())


def local_date(value: datetime | None, tz: tzinfo) -> str:
    """Return YYYY-MM-DD in the user's timezone."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(tz).date().isoformat()


def iso_to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def is_date_string(value: str | None) -> bool:
    return bool(value and _ISO_DATE.match(value))


# ---------------------------------------------------------------------------
# Text / identifiers
# ---------------------------------------------------------------------------

def normalize_key(value: str | None) -> str:
    """Case- and umlaut-insensitive comparison key."""
    if not value:
        return ""
    folded = value.casefold()
    folded = folded.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    folded = folded.replace("ß", "ss")
    folded = unicodedata.normalize("NFKD", folded)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def normalize_tracking(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def slugify(value: str | None, fallback: str = "package") -> str:
    key = normalize_key(value)
    slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    return slug[:40] or fallback


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    visible = local[:1]
    return f"{visible}***@{domain}"


def mask_tracking(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 6:
        return "***"
    return f"{value[:4]}…{value[-3:]}"


def truncate(value: str | None, length: int = 400) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip() + "…"


def clean_whitespace(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def strip_html(value: str) -> str:
    return clean_whitespace(html_to_text(value))


def build_tracking_url(carrier: str | None, tracking: str | None) -> str | None:
    if not carrier or not tracking:
        return None
    template = TRACKING_URL_TEMPLATES.get(carrier)
    if not template:
        return None
    return template.format(tracking=tracking)


def carrier_name(carrier: str | None) -> str | None:
    if not carrier:
        return None
    return CARRIER_NAMES.get(carrier, carrier)


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def absolute_url(value: str | None, base: str | None = None) -> str | None:
    if not value:
        return None
    value = unescape(value).strip()
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/") and base:
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}{value}"
    if is_http_url(value):
        return value
    return None


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_SKIP_TAGS: Final = {"script", "style", "noscript", "template", "svg", "head"}
_BLOCK_TAGS: Final = {
    "p",
    "div",
    "br",
    "tr",
    "td",
    "th",
    "li",
    "ul",
    "ol",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "section",
    "article",
    "header",
    "footer",
    "blockquote",
}


class _HTMLCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}
        self._skip_depth = 0
        self._link_href: str | None = None
        self._link_depth = 0
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): (value or "") for key, value in attrs}
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in _BLOCK_TAGS:
            self.text_parts.append("\n")
        if tag == "meta":
            name = (attr.get("property") or attr.get("name") or "").lower()
            if name in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
                if attr.get("content"):
                    self.meta.setdefault(name, attr["content"])
        elif tag == "img":
            self.images.append(
                {
                    "src": attr.get("src", ""),
                    "alt": attr.get("alt", ""),
                    "width": attr.get("width", ""),
                    "height": attr.get("height", ""),
                }
            )
            if attr.get("alt"):
                self.text_parts.append(f"\n{attr['alt']}\n")
        elif tag == "a":
            if self._link_href is None:
                self._link_href = attr.get("href", "")
                self._link_depth = 0
                self._link_text = []
            else:
                self._link_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._link_href is not None:
            if self._link_depth:
                self._link_depth -= 1
            else:
                text = clean_whitespace(" ".join(self._link_text))
                if self._link_href:
                    self.links.append((self._link_href, text))
                self._link_href = None
                self._link_text = []
        if tag in _BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._link_href is not None:
            self._link_text.append(data)
        self.text_parts.append(data)

    def close(self) -> None:
        super().close()
        # Real-world HTML is often truncated or missing closing tags.  Keep
        # the text of an unterminated link instead of losing it.
        if self._link_href is not None:
            text = clean_whitespace(" ".join(self._link_text))
            if text:
                self.links.append((self._link_href, text))
            self._link_href = None
            self._link_text = []


def _parse_html(html: str) -> _HTMLCollector:
    collector = _HTMLCollector()
    try:
        collector.feed(html[:1_000_000])
        collector.close()
    except Exception:  # noqa: BLE001 - malformed HTML must never break parsing
        pass
    return collector


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    collector = _parse_html(html)
    text = "".join(collector.text_parts)
    # Convert block markers to single newlines and collapse whitespace.
    lines = [clean_whitespace(line) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def extract_html_details(html: str | None) -> dict[str, object]:
    if not html:
        return {"links": [], "images": [], "meta": {}}
    collector = _parse_html(html)
    return {
        "links": collector.links,
        "images": collector.images,
        "meta": collector.meta,
        "text": html_to_text(html),
    }


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_MONTHS: Final[dict[str, int]] = {
    "januar": 1,
    "jan": 1,
    "january": 1,
    "februar": 2,
    "feb": 2,
    "february": 2,
    "maerz": 3,
    "märz": 3,
    "mrz": 3,
    "mar": 3,
    "march": 3,
    "april": 4,
    "apr": 4,
    "mai": 5,
    "may": 5,
    "juni": 6,
    "jun": 6,
    "june": 6,
    "juli": 7,
    "jul": 7,
    "july": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "october": 10,
    "november": 11,
    "nov": 11,
    "dezember": 12,
    "dez": 12,
    "dec": 12,
    "december": 12,
}

_WEEKDAYS: Final[dict[str, int]] = {
    "montag": 0,
    "monday": 0,
    "dienstag": 1,
    "tuesday": 1,
    "mittwoch": 2,
    "wednesday": 2,
    "donnerstag": 3,
    "thursday": 3,
    "freitag": 4,
    "friday": 4,
    "samstag": 5,
    "saturday": 5,
    "sonnabend": 5,
    "sonntag": 6,
    "sunday": 6,
}

_DELIVERY_CONTEXT = re.compile(
    r"(zustell|zugestellt|geliefert|liefer|ankunft|erwartet|voraussichtlich|"
    r"delivery|delivered|deliver|arriv|expected|kommt|eintreff|zeitfenster|"
    r"bis spätestens|no later)",
    re.IGNORECASE,
)

_DATE_DOTTED = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})?\b")
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_NAMED = re.compile(
    r"\b(\d{1,2})\.?\s+(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\b"
    r"(?:\s+(\d{4}))?",
    re.IGNORECASE,
)
_DATE_WEEKDAY = re.compile(
    r"\b(" + "|".join(_WEEKDAYS) + r")\b(?:[,\s]+(\d{1,2})\.(\d{1,2})\.?)?",
    re.IGNORECASE,
)

_RELATIVE = re.compile(
    r"\b(heute|today|morgen|tomorrow|übermorgen|uebermorgen|"
    r"in\s+(\d{1,2})\s+(werktagen|arbeitstagen|tagen|days?|business days?))\b",
    re.IGNORECASE,
)

_TIME_WINDOW_PATTERNS: Final = (
    re.compile(
        r"\b(\d{1,2})[:.](\d{2})\s*(?:uhr)?\s*(?:–|—|-|bis|to)\s*"
        r"(\d{1,2})[:.](\d{2})\s*(?:uhr)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bzwischen\s+(\d{1,2})(?::(\d{2}))?\s*(?:und|and)\s*"
        r"(\d{1,2})(?::(\d{2}))?\s*uhr",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2})\s*(?:–|—|-|bis)\s*(\d{1,2})\s*uhr\b",
        re.IGNORECASE,
    ),
)


def _valid_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _future_adjust(value: date, reference: date, *, max_past_days: int = 2) -> date | None:
    """Interpret dates without a year as the next sensible occurrence."""
    if value < reference - timedelta(days=max_past_days):
        # A date more than two days in the past is almost certainly next year
        # when the year was omitted (e.g. "24.12." in January).
        try:
            candidate = value.replace(year=value.year + 1)
        except ValueError:
            return None
        if candidate >= reference - timedelta(days=max_past_days):
            return candidate
        return None
    return value


def find_dates(
    text: str,
    reference: datetime,
    *,
    allow_past: bool = False,
) -> list[tuple[date, int, str]]:
    """Find dates with their character position and raw match."""
    results: list[tuple[date, int, str]] = []
    ref_date = reference.date()

    for match in _DATE_ISO.finditer(text):
        value = _valid_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if value:
            results.append((value, match.start(), match.group(0)))

    for match in _DATE_DOTTED.finditer(text):
        day, month = int(match.group(1)), int(match.group(2))
        year_raw = match.group(3)
        year = int(year_raw) if year_raw else ref_date.year
        if year_raw and len(year_raw) == 2:
            year += 2000
        value = _valid_date(year, month, day)
        if value and not year_raw:
            value = _future_adjust(value, ref_date)
        if value:
            results.append((value, match.start(), match.group(0)))

    for match in _DATE_NAMED.finditer(text):
        month = _MONTHS.get(match.group(2).casefold().replace("ä", "ae"))
        if month is None:
            month = _MONTHS.get(match.group(2).casefold())
        if month is None:
            continue
        day = int(match.group(1))
        year_raw = match.group(3)
        year = int(year_raw) if year_raw else ref_date.year
        value = _valid_date(year, month, day)
        if value and not year_raw:
            value = _future_adjust(value, ref_date)
        if value:
            results.append((value, match.start(), match.group(0)))

    for match in _DATE_WEEKDAY.finditer(text):
        weekday = _WEEKDAYS.get(match.group(1).casefold())
        if weekday is None:
            continue
        # Explicit weekday + date was already handled above; the weekday
        # itself is only used when no day/month follows.
        if match.group(2):
            continue
        delta = (weekday - ref_date.weekday()) % 7
        if delta == 0 and not allow_past:
            delta = 7
        value = ref_date + timedelta(days=delta)
        results.append((value, match.start(), match.group(0)))

    for match in _RELATIVE.finditer(text):
        token = match.group(1).casefold()
        if token in {"heute", "today"}:
            value = ref_date
        elif token in {"morgen", "tomorrow"}:
            value = ref_date + timedelta(days=1)
        elif token in {"übermorgen", "uebermorgen"}:
            value = ref_date + timedelta(days=2)
        else:
            amount = int(match.group(2) or 0)
            value = ref_date + timedelta(days=amount)
        results.append((value, match.start(), match.group(0)))

    if not allow_past:
        results = [
            item
            for item in results
            if item[0] >= ref_date - timedelta(days=2)
        ]

    # De-duplicate identical dates at nearly identical positions.
    seen: set[tuple[date, int]] = set()
    unique: list[tuple[date, int, str]] = []
    for value, position, raw in sorted(results, key=lambda item: item[1]):
        key = (value, position // 5)
        if key in seen:
            continue
        seen.add(key)
        unique.append((value, position, raw))
    return unique


def find_expected_delivery(
    text: str,
    subject: str,
    reference: datetime,
    *,
    allow_past: bool = False,
    require_context: bool = True,
) -> str | None:
    """Extract the most plausible delivery date from an e-mail."""
    combined = f"{subject}\n{text}"
    dates = find_dates(combined, reference, allow_past=allow_past)
    if not dates:
        return None

    subject_lower = subject.casefold()
    subject_hint = any(
        token in subject_lower
        for token in ("zustellung", "lieferung", "delivery", "kommt", "arrives")
    )

    scored: list[tuple[int, date]] = []
    for value, position, _raw in dates:
        window = combined[max(0, position - 120) : position + 140]
        score = 0
        if _DELIVERY_CONTEXT.search(window):
            score += 3
        if subject_hint:
            score += 1
        # Prefer dates close to a delivery keyword, and future dates.
        if value >= reference.date():
            score += 1
        if value == reference.date():
            score += 1
        if require_context and score < 3 and not subject_hint:
            continue
        scored.append((score, value))

    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1] >= reference.date(), -item[1].toordinal()), reverse=True)
    return scored[0][1].isoformat()


def find_time_window(text: str, subject: str = "") -> str | None:
    combined = f"{subject}\n{text}"
    for index, pattern in enumerate(_TIME_WINDOW_PATTERNS):
        for match in pattern.finditer(combined):
            groups = match.groups()
            if index == 2:
                start_hour, start_min = int(groups[0]), 0
                end_hour, end_min = int(groups[1]), 0
            else:
                start_hour = int(groups[0])
                start_min = int(groups[1] or 0)
                end_hour = int(groups[2])
                end_min = int(groups[3] or 0)
            if not (5 <= start_hour <= 23 and 5 <= end_hour <= 23):
                continue
            if (start_hour, start_min) >= (end_hour, end_min):
                continue
            # Check that the window is plausible (not a support hotline).
            window = combined[max(0, match.start() - 90) : match.end() + 40].casefold()
            if not any(
                token in window
                for token in (
                    "zustell",
                    "liefer",
                    "zeitfenster",
                    "delivery",
                    "zwischen",
                    "kommt",
                    "ankunft",
                )
            ) and not any(token in subject.casefold() for token in ("zustell", "liefer")):
                continue
            return f"{start_hour:02d}:{start_min:02d}–{end_hour:02d}:{end_min:02d} Uhr"
    return None


def date_today(tz: tzinfo) -> str:
    return datetime.now(tz).date().isoformat()
