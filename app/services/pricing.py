import datetime as dt
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _parse_datetime(value: str, tz: dt.tzinfo) -> dt.datetime:
    parsed = dt.datetime.strptime(value, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=tz)


def _load_pricing(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_price_kopeks(
    kind: str,
    *,
    pricing_path: Path,
    now: dt.datetime | None = None,
) -> int:
    data = _load_pricing(pricing_path)
    tz_name = data.get("timezone") or "Europe/Moscow"
    tz_offset_hours = data.get("timezone_offset_hours")
    try:
        tz: dt.tzinfo = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        if tz_offset_hours is None:
            raise
        tz = dt.timezone(dt.timedelta(hours=int(tz_offset_hours)))
    current = now.astimezone(tz) if now else dt.datetime.now(tz=tz)
    price_block = (data.get("prices") or {}).get(kind) or {}
    default_kopeks = int(price_block.get("default_kopeks") or 0)
    for rule in price_block.get("rules") or []:
        rule_type = rule.get("type")
        if not rule_type:
            rule_type = "window" if rule.get("end") else "from"
        if rule_type == "window":
            start = _parse_datetime(rule["start"], tz)
            end = _parse_datetime(rule["end"], tz)
            if start <= current < end:
                return int(rule["price_kopeks"])
        elif rule_type == "from":
            start = _parse_datetime(rule["start"], tz)
            if current >= start:
                return int(rule["price_kopeks"])
        elif rule_type == "until":
            end = _parse_datetime(rule["end"], tz)
            if current < end:
                return int(rule["price_kopeks"])
    return default_kopeks
