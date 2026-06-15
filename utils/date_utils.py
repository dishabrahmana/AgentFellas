from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import settings

TZ = ZoneInfo(settings.tz)


def now() -> datetime:
    return datetime.now(TZ)


def today_start() -> datetime:
    return now().replace(hour=0, minute=0, second=0, microsecond=0)


def today_end() -> datetime:
    return today_start() + timedelta(days=1)


def week_start() -> datetime:
    t = today_start()
    return t - timedelta(days=t.weekday())


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.astimezone(TZ).strftime("%d %b %Y, %H:%M")


def format_date(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.astimezone(TZ).strftime("%d %b %Y")


def format_duration(hours: float | None) -> str:
    if hours is None:
        return "-"
    h = int(hours)
    m = int((hours - h) * 60)
    if h == 0:
        return f"{m}m"
    if m == 0:
        return f"{h}j"
    return f"{h}j {m}m"


def parse_relative_date(text: str) -> datetime | None:
    text = text.lower().strip()
    base = now()

    if text in ("hari ini", "today", "sekarang"):
        return base
    if text in ("besok", "tomorrow"):
        return base + timedelta(days=1)
    if text in ("lusa", "day after tomorrow"):
        return base + timedelta(days=2)
    if text in ("kemarin", "yesterday"):
        return base - timedelta(days=1)

    for word, delta in [("hari", 1), ("minggu", 7), ("bulan", 30)]:
        if word in text:
            try:
                parts = text.split()
                for i, p in enumerate(parts):
                    if p.isdigit():
                        n = int(p)
                        if "depan" in text or "lagi" in text:
                            return base + timedelta(days=n * delta)
                        if "lalu" in text or "kemarin" in text or "yang" in text:
                            return base - timedelta(days=n * delta)
            except (ValueError, IndexError):
                pass

    return None
