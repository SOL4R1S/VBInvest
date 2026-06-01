from __future__ import annotations

from dataclasses import dataclass

from scripts.lib.disclosures import collect_disclosures_for_asset
from scripts.lib.news import collect_news_for_asset, dedupe_news_rows, prepare_news_rows


@dataclass(frozen=True)
class SourceIngestResult:
    failures: list[str]
    provider_disabled: list[dict[str, str]]
    news_items: int
    disclosures: int


def collect_asset_sources(
    asset: dict,
    *,
    no_network: bool,
    dart_api_key: str | None,
    db,
    news_collector=collect_news_for_asset,
    disclosure_collector=collect_disclosures_for_asset,
) -> SourceIngestResult:
    symbol = asset["symbol"]
    news_result = news_collector(asset, no_network=no_network)
    disclosure_result = disclosure_collector(asset, no_network=no_network, dart_api_key=dart_api_key)

    failures = []
    if news_result.status == "failed":
        failures.append(f"{symbol}:NewsFetchError")
    if disclosure_result.status == "failed":
        failures.append(f"{symbol}:DisclosureFetchError")

    news_rows = dedupe_news_rows(prepare_news_rows(asset["asset_id"], news_result.items))
    disclosure_rows = disclosure_result.items
    if db is not None:
        db.upsert_news_items(news_rows)
        db.upsert_disclosures(disclosure_rows)

    return SourceIngestResult(
        failures=failures,
        provider_disabled=[
            _provider_disabled(symbol, item)
            for item in [*news_result.provider_disabled, *disclosure_result.provider_disabled]
        ],
        news_items=len(news_rows),
        disclosures=len(disclosure_rows),
    )


def format_provider_disabled(items: list[dict[str, str]] | None) -> str:
    if not items:
        return "none"
    return ",".join(f"{item['symbol']}:{item['provider']}:{item['reason']}" for item in items)


def _provider_disabled(symbol: str, value: str) -> dict[str, str]:
    provider, separator, reason = value.partition(":")
    return {"symbol": symbol, "provider": provider, "reason": reason if separator else "disabled"}
