"""Batas pemakaian harian (PRD 7.10). Hari dihitung dalam WIB, zona waktu pengguna."""

from datetime import date, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))


def today_wib() -> date:
    return datetime.now(WIB).date()


def start_of_today_wib() -> str:
    now = datetime.now(WIB)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
