from __future__ import annotations

SEMICONDUCTOR_CORE = [
    {"symbol": "SNDK", "display_name_ko": "샌디스크", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "005930.KS", "display_name_ko": "삼성전자", "exchange": "KRX", "currency": "KRW"},
    {"symbol": "000660.KS", "display_name_ko": "SK하이닉스", "exchange": "KRX", "currency": "KRW"},
    {"symbol": "MU", "display_name_ko": "마이크론", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "STX", "display_name_ko": "씨게이트", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "WDC", "display_name_ko": "웨스턴디지털", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "MRVL", "display_name_ko": "마벨", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "042700.KQ", "display_name_ko": "한미반도체", "exchange": "KOSDAQ", "currency": "KRW"},
    {"symbol": "AMAT", "display_name_ko": "어플라이드 머티어리얼즈", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "LRCX", "display_name_ko": "램리서치", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "ASML", "display_name_ko": "ASML 홀딩", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "080220.KQ", "display_name_ko": "제주반도체", "exchange": "KOSDAQ", "currency": "KRW"},
    {"symbol": "TSM", "display_name_ko": "TSMC", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "NVDA", "display_name_ko": "엔비디아", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "AVGO", "display_name_ko": "브로드컴", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "AMD", "display_name_ko": "AMD", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "INTC", "display_name_ko": "인텔", "exchange": "NASDAQ", "currency": "USD"},
]

WATCHLISTS = {"semiconductor-core": SEMICONDUCTOR_CORE}


def get_watchlist_symbols(slug: str) -> list[str]:
    try:
        return [item["symbol"] for item in WATCHLISTS[slug]]
    except KeyError as exc:
        raise ValueError(f"unknown watchlist slug: {slug}") from exc
