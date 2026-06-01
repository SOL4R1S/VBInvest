import json
from datetime import date, datetime, timezone

import pytest

from scripts.lib.research import (
    APPROVED_OPINIONS,
    GuardrailError,
    build_on_demand_research_view,
    build_source_packet,
    validate_research_view,
)


def test_source_packet_has_db_source_or_source_gap():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"date": date(2026, 6, 1), "close": 120, "rsi14": 62}

    packet = build_source_packet(asset, latest, news=[], disclosures=[])

    assert packet["source_gap"] is True
    assert packet["sources"][0]["kind"] == "source_gap"
    assert packet["sources"][0]["symbol"] == "NVDA"


def test_source_packet_includes_news_and_disclosures():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"date": date(2026, 6, 1), "close": 120, "rsi14": 62}
    news = [{"title": "NVIDIA files update", "url": "https://example.com/n", "published_at": datetime(2026, 6, 1, tzinfo=timezone.utc)}]
    disclosures = [{"title": "10-Q Quarterly report", "url": "https://example.com/d", "published_at": datetime(2026, 5, 1, tzinfo=timezone.utc)}]

    packet = build_source_packet(asset, latest, news=news, disclosures=disclosures)

    assert packet["source_gap"] is False
    assert {source["kind"] for source in packet["sources"]} == {"db_price_indicator", "news", "disclosure"}


def test_missing_ai_credentials_use_deterministic_fallback():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"date": date(2026, 6, 1), "return_1m": 0.12, "rsi14": 62, "drawdown_52w": -0.08, "close": 120, "ma20": 110, "ma50": 100}
    packet = build_source_packet(asset, latest, news=[], disclosures=[])

    row = build_on_demand_research_view(asset, latest, packet, ai_credentials_present=False)

    assert row["model_provider"] == "fallback"
    assert row["opinion"] in APPROVED_OPINIONS
    assert row["source_freshness_status"] == "source_gap"
    assert "투자 권유가 아니라" in row["thesis"]


def test_research_view_sources_are_json_serialized_for_db():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"date": date(2026, 6, 1), "return_1m": 0.0, "rsi14": 50, "drawdown_52w": -0.2, "close": 100, "ma20": 100, "ma50": 100}
    packet = build_source_packet(asset, latest, news=[], disclosures=[])

    row = build_on_demand_research_view(asset, latest, packet, ai_credentials_present=False)

    assert json.loads(row["sources"])[0]["kind"] == "source_gap"
    assert json.loads(row["rationale"])
    assert row["confidence"] < 0.7


def test_unsourced_claim_fails_validation():
    row = {
        "opinion": "매수",
        "thesis": "수익을 보장합니다.",
        "sources": json.dumps([]),
    }

    with pytest.raises(GuardrailError):
        validate_research_view(row)
