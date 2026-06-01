from datetime import date
import json

import pytest

from scripts.lib.research import (
    GuardrailError,
    build_on_demand_research_view,
    build_source_packet,
    opinion_from_metrics,
    validate_research_view,
)


def test_opinion_from_metrics_allows_only_five_labels():
    labels = {
        opinion_from_metrics({"return_1m": 0.2, "rsi14": 60, "drawdown_52w": -0.05, "close": 120, "ma20": 110, "ma50": 100}),
        opinion_from_metrics({"return_1m": -0.2, "rsi14": 30, "drawdown_52w": -0.4, "close": 80, "ma20": 90, "ma50": 100}),
        opinion_from_metrics({"return_1m": 0.0, "rsi14": 50, "drawdown_52w": -0.2, "close": 100, "ma20": 100, "ma50": 100}),
    }
    assert labels <= {"매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"}


def test_build_research_row_is_db_upsert_ready_and_secret_free():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"return_1m": 0.12, "rsi14": 62, "drawdown_52w": -0.08, "close": 120, "ma20": 110, "ma50": 100}
    packet = build_source_packet(asset, latest, news=[], disclosures=[])

    row = build_on_demand_research_view(asset, latest, packet, ai_credentials_present=False)

    assert row["target_type"] == "asset"
    assert row["target_slug"] == "NVDA"
    assert row["horizon"] == "on_demand"
    assert row["opinion"] in {"매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"}
    assert isinstance(row["report_date"], date)
    assert "투자 권유가 아니라" in row["thesis"]
    assert row["model_provider"] == "fallback"
    assert row["source_freshness_status"] in {"fresh", "source_gap"}
    assert "password" not in str(row).lower()


class FakeAIResearchClient:
    def generate_research(self, asset, latest, packet):
        return {
            "opinion": "아웃퍼폼",
            "thesis": "DB 가격 지표와 공개 소스를 바탕으로 다음 주 모멘텀 개선 가능성을 점검합니다.",
            "rationale": ["RSI14가 과열권 밖에 있습니다.", "최근 수익률이 개선됐습니다."],
            "bull": "AI 서버 수요가 추가 업사이드를 만들 수 있습니다.",
            "base": "현재 지표는 점진적 개선을 가리킵니다.",
            "bear": "CAPEX 둔화와 재고 조정은 하방 리스크입니다.",
            "risks": ["수요 둔화", "마진 압박"],
            "triggers": ["실적 발표", "가이던스"],
            "confidence": 0.68,
        }


def test_build_on_demand_research_view_uses_ai_provider_draft_with_source_packet():
    asset = {"symbol": "NVDA", "display_name_ko": "엔비디아"}
    latest = {"date": "2026-05-29", "return_1m": 0.08, "rsi14": 58, "drawdown_52w": -0.1, "close": 120}
    packet = build_source_packet(
        asset,
        latest,
        news=[{"title": "AI server demand", "url": "https://example.com/news", "published_at": "2026-05-29"}],
        disclosures=[],
    )

    row = build_on_demand_research_view(
        asset,
        latest,
        packet,
        ai_credentials_present=True,
        model_provider="example-ai",
        ai_client=FakeAIResearchClient(),
    )

    assert row["opinion"] == "아웃퍼폼"
    assert row["model_provider"] == "example-ai"
    assert row["model_name"] == "openai-compatible"
    assert row["confidence"] == 0.68
    assert "투자 권유" not in row["thesis"]
    assert json.loads(row["sources"])[0]["kind"] == "db_price_indicator"


def test_unsourced_claim_fails_validation():
    row = {
        "opinion": "매수",
        "thesis": "수익을 보장합니다.",
        "sources": json.dumps([]),
    }

    with pytest.raises(GuardrailError):
        validate_research_view(row)
