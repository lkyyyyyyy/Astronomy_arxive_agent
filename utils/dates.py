from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


REPORT_WINDOW_START_HOUR = 8


def previous_day(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date() - timedelta(days=1)


def parse_date(value: str | None, timezone: str) -> date:
    if value:
        return date.fromisoformat(value)
    return previous_day(timezone)


def report_window(target_date: date, timezone: str) -> tuple[datetime, datetime]:
    """Return the local 08:00-to-08:00 reporting window for target_date."""
    tz = ZoneInfo(timezone)
    start = datetime.combine(target_date, time(REPORT_WINDOW_START_HOUR), tzinfo=tz)
    return start, start + timedelta(days=1)


def format_beijing_window(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return ""
    return f"{start:%Y-%m-%d %H:%M} 至 {end:%Y-%m-%d %H:%M}，北京时间"
