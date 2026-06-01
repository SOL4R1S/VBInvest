from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.lib.market_calendar import completed_trade_date, summarize_trade_dates


def test_completed_trade_date_at_1700_kst_uses_current_krx_day_and_previous_us_day():
    at_kst = datetime(2026, 6, 1, 17, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    krx_date = completed_trade_date("KRX", at_kst)
    us_date = completed_trade_date("NASDAQ", at_kst)

    assert krx_date.isoformat() == "2026-06-01"
    assert us_date.isoformat() == "2026-05-29"


def test_completed_trade_date_skips_weekends():
    at_kst = datetime(2026, 6, 7, 17, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    assert completed_trade_date("KRX", at_kst).isoformat() == "2026-06-05"
    assert completed_trade_date("NYSE", at_kst).isoformat() == "2026-06-05"


def test_summarize_trade_dates_groups_by_market_family():
    at_kst = datetime(2026, 6, 1, 17, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    assets = [
        {"symbol": "NVDA", "exchange": "NASDAQ"},
        {"symbol": "005930.KS", "exchange": "KRX"},
    ]

    summary = summarize_trade_dates(assets, at_kst)

    assert summary == "KRX:2026-06-01,US:2026-05-29"
