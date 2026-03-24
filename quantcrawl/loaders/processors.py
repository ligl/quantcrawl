from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def clean_text(value: object) -> str:
    text = str(value or "").strip()
    return " ".join(text.split())


def normalize_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, query, ""))


def to_utc_iso(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC).isoformat()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).isoformat()
    return dt.astimezone(UTC).isoformat()
