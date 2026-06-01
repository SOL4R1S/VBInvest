from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Protocol


APPROVED_OPINIONS = {"매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"}
FORBIDDEN_RESEARCH_PHRASES = ("수익을 보장", "보장합니다", "guaranteed return", "risk-free")


class GuardrailError(ValueError):
    pass


class ResearchAIClient(Protocol):
    def generate_research(self, asset: dict[str, Any], latest: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
        ...


def build_source_packet(
    asset: dict[str, Any],
    latest: dict[str, Any],
    *,
    news: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> dict[str, Any]:
    symbol = asset["symbol"]
    sources: list[dict[str, Any]] = []
    source_gap = not news and not disclosures
    if source_gap:
        sources.append({"kind": "source_gap", "symbol": symbol, "reason": "no recent news or disclosures"})
    else:
        sources.append(
            {
                "kind": "db_price_indicator",
                "symbol": symbol,
                "date": _json_value(latest.get("date")),
                "fields": ["close", "return_1m", "rsi14", "drawdown_52w", "ma20", "ma50"],
            }
        )
        sources.extend(_source_rows("news", symbol, news))
        sources.extend(_source_rows("disclosure", symbol, disclosures))
    return {"asset": asset, "latest": latest, "sources": sources, "source_gap": source_gap}


def build_on_demand_research_view(
    asset: dict[str, Any],
    latest: dict[str, Any],
    packet: dict[str, Any],
    *,
    ai_credentials_present: bool,
    model_provider: str | None = None,
    ai_client: ResearchAIClient | None = None,
) -> dict[str, Any]:
    provider = model_provider or ("configured-ai" if ai_credentials_present else "fallback")
    row = _ai_view(asset, latest, packet, provider, ai_client) if ai_client is not None else _fallback_view(asset, latest, packet, provider)
    validate_research_view(row)
    return row


def opinion_from_metrics(latest: dict[str, Any]) -> str:
    rsi = _as_float(latest.get("rsi14"))
    ret_1m = _as_float(latest.get("return_1m"))
    dd = _as_float(latest.get("drawdown_52w"))
    ma20 = _as_float(latest.get("ma20"))
    ma50 = _as_float(latest.get("ma50"))
    close = _as_float(latest.get("close"))
    score = 0
    if ret_1m is not None:
        score += 2 if ret_1m > 0.12 else 1 if ret_1m > 0.03 else -1 if ret_1m < -0.08 else 0
    if close and ma20 and close > ma20:
        score += 1
    if close and ma50 and close > ma50:
        score += 1
    if rsi is not None:
        score += 1 if 50 <= rsi <= 68 else -1 if rsi > 78 or rsi < 35 else 0
    if dd is not None:
        score += -1 if dd < -0.30 else 1 if dd > -0.12 else 0
    if score >= 4:
        return "매수"
    if score >= 2:
        return "아웃퍼폼"
    if score <= -3:
        return "매도"
    if score <= -1:
        return "언더퍼폼"
    return "중립"


def validate_research_view(row: dict[str, Any]) -> None:
    if row.get("opinion") not in APPROVED_OPINIONS:
        raise GuardrailError(f"unapproved opinion: {row.get('opinion')}")
    thesis = str(row.get("thesis") or "").lower()
    if any(phrase in thesis for phrase in FORBIDDEN_RESEARCH_PHRASES):
        raise GuardrailError("forbidden investment promise")
    sources = _json_loads(row.get("sources"))
    has_source_gap = any(source.get("kind") == "source_gap" for source in sources if isinstance(source, dict))
    if not sources and not has_source_gap:
        raise GuardrailError("research row requires sources or source_gap")


def _fallback_view(asset: dict[str, Any], latest: dict[str, Any], packet: dict[str, Any], provider: str) -> dict[str, Any]:
    symbol = asset["symbol"]
    name = asset.get("display_name_ko") or symbol
    opinion = opinion_from_metrics(latest)
    rationale = [
        _metric_sentence("최근 1개월 수익률", latest.get("return_1m"), percent=True),
        _metric_sentence("RSI14", latest.get("rsi14"), percent=False),
        _metric_sentence("52주 고점 대비", latest.get("drawdown_52w"), percent=True),
    ]
    source_status = "source_gap" if packet["source_gap"] else "fresh"
    confidence = 0.55 if packet["source_gap"] else 0.72
    thesis = (
        f"{name} ({symbol})는 확인된 DB 가격·지표와 최근 소스 상태를 기준으로 `{opinion}`로 분류합니다. "
        "이는 투자 권유가 아니라 사용자가 요청한 리서치용 의견입니다."
    )
    return {
        "target_type": "asset",
        "target_slug": symbol,
        "report_date": date.today(),
        "horizon": "on_demand",
        "opinion": opinion,
        "thesis": thesis,
        "rationale": json.dumps(rationale, ensure_ascii=False),
        "bull": "AI 서버/메모리/스토리지/장비 수요와 실적 가이던스가 동시에 개선되면 업사이드가 커질 수 있습니다.",
        "base": "현재 확인된 가격·지표 흐름과 공개 소스의 신선도를 기준으로 섹터 내 상대 모멘텀을 점검합니다.",
        "bear": "수요 둔화, 재고 조정, 과도한 밸류에이션, 금리·환율 변수는 하방 리스크입니다.",
        "risks": json.dumps(["실적/가이던스 하향", "AI 투자 사이클 둔화", "환율·금리 변동", "지정학/수출규제"], ensure_ascii=False),
        "triggers": json.dumps(["실적 발표", "메모리 가격", "CAPEX 코멘트", "AI 서버 주문", "장비 발주"], ensure_ascii=False),
        "sources": json.dumps(packet["sources"], ensure_ascii=False, default=str),
        "model_provider": provider,
        "model_name": "deterministic-fallback" if provider == "fallback" else "mock-research-adapter",
        "confidence": confidence,
        "source_freshness_status": source_status,
        "access_tier": "free",
    }


def _ai_view(
    asset: dict[str, Any],
    latest: dict[str, Any],
    packet: dict[str, Any],
    provider: str,
    ai_client: ResearchAIClient,
) -> dict[str, Any]:
    draft = ai_client.generate_research(asset, latest, packet)
    return {
        "target_type": "asset",
        "target_slug": asset["symbol"],
        "report_date": date.today(),
        "horizon": "on_demand",
        "opinion": _required_text(draft, "opinion"),
        "thesis": _required_text(draft, "thesis"),
        "rationale": json.dumps(_string_list(draft.get("rationale")), ensure_ascii=False),
        "bull": _required_text(draft, "bull"),
        "base": _required_text(draft, "base"),
        "bear": _required_text(draft, "bear"),
        "risks": json.dumps(_string_list(draft.get("risks")), ensure_ascii=False),
        "triggers": json.dumps(_string_list(draft.get("triggers")), ensure_ascii=False),
        "sources": json.dumps(packet["sources"], ensure_ascii=False, default=str),
        "model_provider": str(draft.get("model_provider") or provider),
        "model_name": str(draft.get("model_name") or "openai-compatible"),
        "confidence": _confidence(draft.get("confidence")),
        "source_freshness_status": "source_gap" if packet["source_gap"] else "fresh",
        "access_tier": "free",
    }


def _source_rows(kind: str, symbol: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append(
            {
                "kind": kind,
                "symbol": symbol,
                "title": row.get("title"),
                "url": row.get("url"),
                "published_at": _json_value(row.get("published_at")),
            }
        )
    return result


def _metric_sentence(label: str, value: Any, *, percent: bool) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return f"{label} 확인 필요"
    if percent:
        return f"{label} {numeric * 100:+.1f}%"
    return f"{label} {numeric:.1f}"


def _required_text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GuardrailError(f"AI research draft missing text field: {key}")
    return value.strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _confidence(value: Any) -> float:
    numeric = _as_float(value)
    if numeric is None:
        return 0.5
    return max(0.0, min(1.0, numeric))


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_loads(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    return value if isinstance(value, list) else []


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
