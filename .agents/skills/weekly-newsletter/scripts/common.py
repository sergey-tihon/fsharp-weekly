from __future__ import annotations

import json
import re
import urllib.parse
import os
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]


def resolve_output(value: str | None, today: date | None = None) -> tuple[int, int, Path]:
    today = today or date.today()
    iso = today.isocalendar()
    year, week = iso.year, iso.week
    if value and value.strip():
        cleaned = value.strip().lower().removeprefix("week-")
        match = re.fullmatch(r"(?:(\d{4})[-/])?(\d{1,2})", cleaned)
        if not match:
            raise ValueError(f"Invalid week '{value}'")
        year = int(match.group(1) or iso.year)
        week = int(match.group(2))
        date.fromisocalendar(year, week, 1)
    data_root = Path(os.environ.get("FSHARP_WEEKLY_DATA_DIR", ROOT / "data"))
    if not data_root.is_absolute():
        data_root = ROOT / data_root
    return year, week, data_root / str(year) / f"week-{week:02d}"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def normalize_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(value.strip())
    except ValueError:
        return value.strip()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, item) for key, item in query if not key.lower().startswith("utm_") and key.lower() not in {"ref", "ref_src"}]
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, urllib.parse.urlencode(query), ""))


def candidate_id(prefix: str, value: str) -> str:
    import hashlib

    return f"{prefix}-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:8]}"


def nuget_identity(url: str, text: str = "") -> tuple[str, str | None] | None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() not in {"nuget.org", "www.nuget.org"}:
        return None
    match = re.match(r"/packages/([^/]+)(?:/([^/]+))?", parsed.path, re.IGNORECASE)
    if not match:
        return None
    package = urllib.parse.unquote(match.group(1)).lower()
    version = urllib.parse.unquote(match.group(2)) if match.group(2) else None
    if not version and text:
        text_match = re.search(rf"\b{re.escape(urllib.parse.unquote(match.group(1)))}\s+([0-9][0-9A-Za-z.+-]*)", text, re.IGNORECASE)
        version = text_match.group(1) if text_match else None
    return package, version.lower() if version else None
