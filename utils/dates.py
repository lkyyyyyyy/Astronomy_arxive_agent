from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def previous_day(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date() - timedelta(days=1)


def parse_date(value: str | None, timezone: str) -> date:
    if value:
        return date.fromisoformat(value)
    return previous_day(timezone)

