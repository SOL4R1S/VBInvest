"""Tests for scripts.lib.source_ingest — provider disabled formatting."""

from scripts.lib.source_ingest import SourceIngestResult, _provider_disabled, format_provider_disabled


def test_format_provider_disabled_empty():
    assert format_provider_disabled(None) == "none"
    assert format_provider_disabled([]) == "none"


def test_format_provider_disabled_items():
    items = [
        {"symbol": "NVDA", "provider": "news", "reason": "rate_limited"},
        {"symbol": "AAPL", "provider": "dart", "reason": "no_key"},
    ]
    result = format_provider_disabled(items)
    assert "NVDA:news:rate_limited" in result
    assert "AAPL:dart:no_key" in result


def test_provider_disabled_with_separator():
    result = _provider_disabled("NVDA", "news:rate_limited")
    assert result == {"symbol": "NVDA", "provider": "news", "reason": "rate_limited"}


def test_provider_disabled_without_separator():
    result = _provider_disabled("AAPL", "dart")
    assert result == {"symbol": "AAPL", "provider": "dart", "reason": "disabled"}


def test_source_ingest_result_dataclass():
    result = SourceIngestResult(
        failures=["NVDA:NewsFetchError"],
        provider_disabled=[{"symbol": "NVDA", "provider": "news", "reason": "timeout"}],
        news_items=5,
        disclosures=2,
    )
    assert result.failures == ["NVDA:NewsFetchError"]
    assert result.news_items == 5
    assert result.disclosures == 2
