"""Natural-language delivery date parsing (typed users don't write ISO dates)."""

from __future__ import annotations

import re
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2,
    "wed": 2, "thursday": 3, "thu": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
# Ordinals that belong to a gift phrase, not a delivery date ("30th birthday").
_GIFT_NOUN_AFTER = re.compile(r"(?i)^\s*(birthday|bday|anniversary|wedding|party|celebration)")

_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAY_ALT = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))

ISO_RE = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
MONTH_DAY_RE = re.compile(rf"(?i)\b({_MONTH_ALT})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b")
DAY_MONTH_RE = re.compile(rf"(?i)\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_ALT})\b")
RELATIVE_RE = re.compile(r"(?i)\b(day after tomorrow|tomorrow|today|tonight)\b")
WEEKDAY_RE = re.compile(rf"(?i)\b(next\s+|this\s+|on\s+)?({_WEEKDAY_ALT})\b")
ORDINAL_RE = re.compile(r"(?i)(?:\bon\s+|\bby\s+|\bthe\s+)?\b(\d{1,2})(st|nd|rd|th)\b")


def _iso(d: date) -> str:
    return d.isoformat()


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_natural_date(
    text: str,
    *,
    today: date | None = None,
    aggressive: bool = False,
) -> tuple[str, int, int] | None:
    """Return (iso_date, start, end) for the first date phrase, or None.

    ``aggressive`` enables loose forms (bare ordinals like "30th", weekdays,
    relative words) that are only safe when we're expecting a delivery date.
    """
    today = today or date.today()

    iso = ISO_RE.search(text)
    if iso:
        year, month, day = (int(g) for g in iso.groups())
        if _safe_date(year, month, day):
            return f"{year:04d}-{month:02d}-{day:02d}", iso.start(), iso.end()

    for rx, order in ((MONTH_DAY_RE, "md"), (DAY_MONTH_RE, "dm")):
        m = rx.search(text)
        if not m:
            continue
        if order == "md":
            month = _MONTHS[m.group(1).lower()]
            day = int(m.group(2))
        else:
            day = int(m.group(1))
            month = _MONTHS[m.group(2).lower()]
        cand = _safe_date(today.year, month, day)
        if cand is None:
            continue
        if cand < today:
            cand = _safe_date(today.year + 1, month, day)
            if cand is None:
                continue
        return _iso(cand), m.start(), m.end()

    if not aggressive:
        return None

    rel = RELATIVE_RE.search(text)
    if rel:
        word = rel.group(1).lower()
        delta = {"today": 0, "tonight": 0, "tomorrow": 1, "day after tomorrow": 2}[word]
        return _iso(today + timedelta(days=delta)), rel.start(), rel.end()

    wk = WEEKDAY_RE.search(text)
    if wk:
        target = _WEEKDAYS[wk.group(2).lower()]
        ahead = (target - today.weekday()) % 7
        if ahead == 0:
            ahead = 7
        return _iso(today + timedelta(days=ahead)), wk.start(), wk.end()

    ordn = ORDINAL_RE.search(text)
    if ordn:
        if _GIFT_NOUN_AFTER.match(text[ordn.end():]):
            return None  # "30th birthday" is a gift phrase, not a date
        day = int(ordn.group(1))
        if 1 <= day <= 31:
            cand = _safe_date(today.year, today.month, day)
            if cand is None or cand < today:
                month = today.month + 1
                year = today.year
                if month > 12:
                    month, year = 1, year + 1
                cand = _safe_date(year, month, day)
            if cand is not None:
                return _iso(cand), ordn.start(), ordn.end()

    return None


_DELIVERY_FILLER = re.compile(
    r"(?i)\b(deliver(?:y)?(?:\s+to)?|send(?:\s+to)?|ship(?:\s+to)?|to|on|in|by|the|of|"
    r"please|city|location|for|at)\b"
)


def extract_delivery_city_and_date(
    text: str,
    *,
    aggressive: bool = False,
    today: date | None = None,
) -> tuple[str | None, str | None]:
    """Pull a delivery (city, iso_date) pair from natural text like 'kandy 30th'."""
    parsed = parse_natural_date(text, today=today, aggressive=aggressive)
    if not parsed:
        return None, None
    iso, start, end = parsed

    remainder = f"{text[:start]} {text[end:]}"
    remainder = _DELIVERY_FILLER.sub(" ", remainder)
    remainder = re.sub(r"[,.;:]", " ", remainder)
    city = re.sub(r"\s+", " ", remainder).strip()

    # A leftover that is a carousel pick or checkout word means this isn't a
    # "city + date" delivery reply (e.g. "the 5th option") — discard entirely.
    if city and re.search(
        r"(?i)\b(option|options|item|items|product|products|choice|result|results|"
        r"one|ones|first|second|third|fourth|fifth|checkout|recipient|sender|phone|"
        r"mobile|address|name is|gift message)\b",
        city,
    ):
        return None, None
    return (city or None), iso
