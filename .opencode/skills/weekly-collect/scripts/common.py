from __future__ import annotations

import json
import gzip
import re
import subprocess
import urllib.error
import urllib.request
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
USER_AGENT = "fsharp-weekly/1.0 (+https://sergeytihon.com/fsharp-weekly/)"


@dataclass(frozen=True)
class RunContext:
    year: int
    week: int
    date_from: date
    date_to: date
    output_dir: Path
    dry_run: bool = False


def resolve_context(value: str | None, dry_run: bool = False, today: date | None = None) -> RunContext:
    today = today or date.today()
    iso = today.isocalendar()
    year, week = iso.year, iso.week

    if value and value.strip():
        cleaned = value.strip().lower().removeprefix("week-")
        match = re.fullmatch(r"(?:(\d{4})[-/])?(\d{1,2})", cleaned)
        if not match:
            raise ValueError(f"Invalid week '{value}'. Use 38, week-38, 2026-38, or 2026/38.")
        year = int(match.group(1) or iso.year)
        week = int(match.group(2))
        if not 1 <= week <= 53:
            raise ValueError("Week must be between 1 and 53.")
        date.fromisocalendar(year, week, 1)

    data_root = Path(os.environ.get("FSHARP_WEEKLY_DATA_DIR", ROOT / "data"))
    if not data_root.is_absolute():
        data_root = ROOT / data_root
    output_dir = data_root / str(year) / f"week-{week:02d}"
    return RunContext(year, week, today - timedelta(days=14), today, output_dir, dry_run)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def in_window(value: str | None, context: RunContext) -> bool:
    parsed = parse_date(value)
    return parsed is not None and context.date_from <= parsed.date() <= context.date_to


def request_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[bytes, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml, */*"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body, response.headers


def request_json(url: str, headers: dict[str, str] | None = None) -> tuple[Any, Any]:
    body, response_headers = request_bytes(url, headers)
    return json.loads(body), response_headers


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def envelope(context: RunContext, source: str, items: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "source": source,
        "scrapedAt": iso_now(),
        "weekNumber": context.week,
        "year": context.year,
        "dateFrom": context.date_from.isoformat(),
        "dateTo": context.date_to.isoformat(),
        "items": items,
        **extra,
    }


def run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)


def parse_cli_json(output: str) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("playwright-cli returned no JSON")
