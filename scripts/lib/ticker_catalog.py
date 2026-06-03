from __future__ import annotations

import html
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
from typing import Final, TypedDict

KIND_LISTED_COMPANY_URL: Final = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"


class TickerCatalogSuggestion(TypedDict):
    symbol: str
    name: str
    exchange: str
    quote_type: str


@dataclass(frozen=True, slots=True)
class ListedTicker:
    name: str
    symbol: str
    market: str


@dataclass(frozen=True, slots=True)
class TickerCatalogLoad:
    catalog: tuple[ListedTicker, ...]
    status: str
    source: str
    reason: str


@dataclass(frozen=True, slots=True)
class TickerCatalogRefreshResult:
    status: str
    count: int
    source: str
    reason: str


FALLBACK_KOREAN_TICKERS: Final[tuple[ListedTicker, ...]] = (
    ListedTicker("삼성전자", "005930.KS", "KSC"),
    ListedTicker("삼성전자우", "005935.KS", "KSC"),
    ListedTicker("삼성전기", "009150.KS", "KSC"),
    ListedTicker("삼성SDI", "006400.KS", "KSC"),
    ListedTicker("삼성바이오로직스", "207940.KS", "KSC"),
    ListedTicker("삼성물산", "028260.KS", "KSC"),
    ListedTicker("SK하이닉스", "000660.KS", "KSC"),
    ListedTicker("SK텔레콤", "017670.KS", "KSC"),
    ListedTicker("SK스퀘어", "402340.KS", "KSC"),
    ListedTicker("SK이노베이션", "096770.KS", "KSC"),
    ListedTicker("SK바이오사이언스", "302440.KS", "KSC"),
    ListedTicker("SKC", "011790.KS", "KSC"),
)


class KRXTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_cell = False
        self._current_cell_parts: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"td", "th"}:
            self._in_cell = True
            self._current_cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"td", "th"} and self._in_cell:
            self._current_row.append(_clean_cell("".join(self._current_cell_parts)))
            self._current_cell_parts = []
            self._in_cell = False
        if normalized == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []


def search_korean_ticker_catalog(query: str, *, limit: int = 8) -> list[TickerCatalogSuggestion]:
    key = _search_key(query)
    if not key:
        return []
    priority = _ranked_catalog_matches(key, FALLBACK_KOREAN_TICKERS)
    priority_symbols = {item.symbol for item in priority}
    catalog = tuple(item for item in load_korean_ticker_catalog() if item.symbol not in priority_symbols)
    ranked = [*priority, *_ranked_catalog_matches(key, catalog)]
    return [_suggestion_from_listed_ticker(item) for item in ranked[:limit]]


def _ranked_catalog_matches(query_key: str, catalog: tuple[ListedTicker, ...]) -> list[ListedTicker]:
    matches: list[tuple[int, int, ListedTicker]] = []
    for index, item in enumerate(catalog):
        score, _ = _ticker_match_score(query_key, item)
        if score is not None:
            matches.append((score, index, item))
    ranked = sorted(matches, key=lambda match: (match[0], match[1]))
    return [item for _, _, item in ranked]


@lru_cache(maxsize=1)
def load_korean_ticker_catalog() -> tuple[ListedTicker, ...]:
    return _cached_korean_ticker_catalog().catalog


def refresh_ticker_catalog() -> TickerCatalogRefreshResult:
    _cached_korean_ticker_catalog.cache_clear()
    load_korean_ticker_catalog.cache_clear()
    loaded = _cached_korean_ticker_catalog()
    return TickerCatalogRefreshResult(
        status=loaded.status,
        count=len(loaded.catalog),
        source=loaded.source,
        reason=loaded.reason,
    )


@lru_cache(maxsize=1)
def _cached_korean_ticker_catalog() -> TickerCatalogLoad:
    try:
        html_text = _download_kind_listed_company_html()
    except (TimeoutError, urllib.error.URLError, UnicodeDecodeError) as exc:
        return TickerCatalogLoad(FALLBACK_KOREAN_TICKERS, "fallback", "fallback", str(exc))
    parsed = parse_kind_listed_company_html(html_text)
    if not parsed:
        return TickerCatalogLoad(FALLBACK_KOREAN_TICKERS, "fallback", "fallback", "empty kind catalog")
    return TickerCatalogLoad(parsed, "ok", "kind", "")


def parse_kind_listed_company_html(html_text: str) -> tuple[ListedTicker, ...]:
    parser = KRXTableParser()
    parser.feed(html_text)
    if not parser.rows:
        return ()
    headers = parser.rows[0]
    try:
        name_index = headers.index("회사명")
        market_index = headers.index("시장구분")
        code_index = headers.index("종목코드")
    except ValueError:
        return ()

    tickers: list[ListedTicker] = []
    for row in parser.rows[1:]:
        if len(row) <= max(name_index, market_index, code_index):
            continue
        symbol = _yfinance_symbol(row[code_index], row[market_index])
        if symbol is None:
            continue
        tickers.append(ListedTicker(row[name_index], symbol, _exchange_code(row[market_index])))
    return tuple(tickers)


def _download_kind_listed_company_html() -> str:
    request = urllib.request.Request(KIND_LISTED_COMPANY_URL, headers={"User-Agent": "VBinvest/0.1"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read().decode("euc-kr")


def _ticker_match_score(query_key: str, item: ListedTicker) -> tuple[int | None, ListedTicker]:
    name_key = _search_key(item.name)
    symbol_key = _search_key(item.symbol)
    if name_key.startswith(query_key):
        return (0, item)
    if symbol_key.startswith(query_key):
        return (1, item)
    if query_key in name_key:
        return (2, item)
    if query_key in symbol_key:
        return (3, item)
    return (None, item)


def _suggestion_from_listed_ticker(item: ListedTicker) -> TickerCatalogSuggestion:
    return {
        "symbol": item.symbol,
        "name": item.name,
        "exchange": item.market,
        "quote_type": "EQUITY",
    }


def _yfinance_symbol(code: str, market: str) -> str | None:
    normalized = code.strip()
    if len(normalized) != 6 or not normalized.isdecimal():
        return None
    suffix = ".KQ" if "코스닥" in market else ".KS"
    return f"{normalized}{suffix}"


def _exchange_code(market: str) -> str:
    if "코스닥" in market:
        return "KOE"
    if "코넥스" in market:
        return "KNX"
    return "KSC"


def _clean_cell(value: str) -> str:
    return " ".join(html.unescape(value).split())


def _search_key(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())
