from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS", "US"}
KRX_EXCHANGES = {"KRX", "KOSPI", "KOSDAQ", "KONEX"}


def market_family(exchange: str | None) -> str:
    normalized = (exchange or "").upper()
    if normalized in KRX_EXCHANGES:
        return "KRX"
    if normalized in US_EXCHANGES:
        return "US"
    return "US"


def completed_trade_date(exchange: str | None, at_kst: datetime) -> date:
    current = _as_kst(at_kst).date()
    if market_family(exchange) == "US":
        current -= timedelta(days=1)
    return _previous_weekday(current)


def summarize_trade_dates(assets: list[dict], at_kst: datetime) -> str:
    dates: dict[str, date] = {}
    for asset in assets:
        family = market_family(asset.get("exchange"))
        dates[family] = completed_trade_date(asset.get("exchange"), at_kst)

    ordered = [family for family in ("KRX", "US") if family in dates]
    ordered.extend(sorted(family for family in dates if family not in ordered))
    return ",".join(f"{family}:{dates[family].isoformat()}" for family in ordered)


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def _previous_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current
