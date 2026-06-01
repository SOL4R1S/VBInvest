from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


YAHOO_NEWS_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"


class NewsFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewsFetchResult:
    status: str
    items: list[dict[str, Any]]
    provider_disabled: list[str]


def parse_yahoo_rss(symbol: str, payload: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise NewsFetchError(f"{symbol}: yahoo rss parse failed: {exc}") from exc

    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        url = _text(item, "link")
        if not title or not url:
            continue
        source_id = _text(item, "guid") or canonicalize_url(url)
        rows.append(
            {
                "provider": "yahoo-rss",
                "source": "Yahoo Finance",
                "source_id": source_id,
                "url": url,
                "canonical_url": canonicalize_url(url),
                "title": title,
                "published_at": parse_rfc2822_datetime(_text(item, "pubDate")),
                "language": "en",
                "summary": _text(item, "description"),
                "raw_json": {"symbol": symbol, "source_id": source_id},
            }
        )
    return rows


def fetch_yahoo_news(symbol: str, *, timeout: int = 20) -> list[dict[str, Any]]:
    url = YAHOO_NEWS_RSS_URL.format(symbol=urllib.parse.quote(symbol))
    request = urllib.request.Request(url, headers={"User-Agent": "VBinvest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        raise NewsFetchError(f"{symbol}: yahoo rss fetch failed: {exc}") from exc
    return parse_yahoo_rss(symbol, payload)


def collect_news_for_asset(
    asset: dict[str, Any],
    *,
    no_network: bool = False,
    fetcher=fetch_yahoo_news,
) -> NewsFetchResult:
    symbol = asset["symbol"]
    if no_network:
        return NewsFetchResult(status="provider_disabled", items=[], provider_disabled=["yahoo-rss:no-network"])
    try:
        return NewsFetchResult(status="ok", items=fetcher(symbol), provider_disabled=[])
    except NewsFetchError:
        return NewsFetchResult(status="failed", items=[], provider_disabled=[])


def prepare_news_rows(asset_id: int, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        row = {
            "asset_id": asset_id,
            "provider": item["provider"],
            "source": item.get("source"),
            "source_id": item.get("source_id"),
            "url": item.get("url"),
            "canonical_url": item.get("canonical_url") or canonicalize_url(item.get("url")),
            "title": item["title"],
            "published_at": item.get("published_at"),
            "language": item.get("language"),
            "summary": item.get("summary"),
            "raw_json": item.get("raw_json") or item,
        }
        row["content_hash"] = content_hash(row)
        rows.append(row)
    return rows


def dedupe_news_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key_value = row.get("source_id") or row.get("canonical_url") or row.get("content_hash")
        key = (row["provider"], str(key_value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def content_hash(row: dict[str, Any]) -> str:
    parts = {
        "provider": row.get("provider"),
        "canonical_url": row.get("canonical_url"),
        "title": row.get("title"),
        "published_at": _iso(row.get("published_at")),
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def parse_rfc2822_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text(item: ET.Element, tag: str) -> str | None:
    value = item.findtext(tag)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)
