"""Sector-specific prompt templates for AI research generation.

v1: symbol-based heuristic for sector detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SectorPromptTemplate:
    sector_key: str
    system_addendum: str
    fallback_bull: str
    fallback_base: str
    fallback_bear: str
    fallback_risks: list[str]
    fallback_triggers: list[str]
    key_metrics: list[str]


SECTOR_TEMPLATES: dict[str, SectorPromptTemplate] = {
    "semiconductor": SectorPromptTemplate(
        sector_key="semiconductor",
        system_addendum=(
            "This asset is in the semiconductor sector. Focus on memory pricing, "
            "CAPEX cycles, AI server demand, equipment orders, and foundry utilization."
        ),
        fallback_bull="AI 서버/메모리/스토리지/장비 수요와 실적 가이던스가 동시에 개선되면 업사이드가 커질 수 있습니다.",
        fallback_base="현재 확인된 가격·지표 흐름과 공개 소스의 신선도를 기준으로 섹터 내 상대 모멘텀을 점검합니다.",
        fallback_bear="수요 둔화, 재고 조정, 과도한 밸류에이션, 금리·환율 변수는 하방 리스크입니다.",
        fallback_risks=["실적/가이던스 하향", "AI 투자 사이클 둔화", "환율·금리 변동", "지정학/수출규제"],
        fallback_triggers=["실적 발표", "메모리 가격", "CAPEX 코멘트", "AI 서버 주문", "장비 발주"],
        key_metrics=["memory_price_index", "foundry_utilization", "capex_guidance", "inventory_days"],
    ),
    "biotech": SectorPromptTemplate(
        sector_key="biotech",
        system_addendum=(
            "This asset is in the biotech/pharmaceutical sector. Focus on pipeline milestones, "
            "clinical trial results, regulatory approvals, licensing deals, and cash runway."
        ),
        fallback_bull="파이프라인 임상 성공과 기술이전/라이선스 계약이 동시에 이루어지면 업사이드가 열립니다.",
        fallback_base="현재 임상 단계와 현금 보유량을 기준으로 리스크-리워드를 평가합니다.",
        fallback_bear="임상 실패, 규제 지연, 현금 소진은 주요 하방 리스크입니다.",
        fallback_risks=["임상 실패", "규제 승인 지연", "현금 소진/희석", "경쟁 약물 등장"],
        fallback_triggers=["임상 결과 발표", "FDA/식약처 심사", "기술이전 계약", "실적 발표"],
        key_metrics=["pipeline_stage", "cash_runway_months", "clinical_trial_count"],
    ),
    "finance": SectorPromptTemplate(
        sector_key="finance",
        system_addendum=(
            "This asset is in the financial sector. Focus on interest rate environment, "
            "credit quality, loan growth, NIM trends, and regulatory capital ratios."
        ),
        fallback_bull="금리 환경 개선과 대출 성장, 건전성 지표 호전이 동시에 나타나면 업사이드가 열립니다.",
        fallback_base="현재 NIM, 대출 성장률, 건전성 지표를 기준으로 섹터 내 상대 위치를 평가합니다.",
        fallback_bear="금리 하락에 따른 NIM 축소, 대손 비용 증가, 규제 강화는 하방 리스크입니다.",
        fallback_risks=["NIM 축소", "대손 비용 증가", "부동산 PF 리스크", "규제 강화"],
        fallback_triggers=["기준금리 결정", "실적 발표", "건전성 지표", "배당 정책"],
        key_metrics=["nim", "loan_growth", "npl_ratio", "cet1_ratio"],
    ),
    "default": SectorPromptTemplate(
        sector_key="default",
        system_addendum="",
        fallback_bull="매출 성장과 마진 개선이 동시에 나타나면 업사이드가 열립니다.",
        fallback_base="현재 확인된 가격·지표 흐름과 공개 소스를 기준으로 펀더멘털을 점검합니다.",
        fallback_bear="매출 둔화, 비용 증가, 경쟁 심화, 매크로 변수는 하방 리스크입니다.",
        fallback_risks=["실적 부진", "경쟁 심화", "매크로 둔화", "규제 변화"],
        fallback_triggers=["실적 발표", "가이던스", "산업 데이터", "정책 변화"],
        key_metrics=["revenue_growth", "operating_margin", "free_cash_flow"],
    ),
}

# Symbol-based heuristic (v1). Extend with sector DB column later.
_SYMBOL_SECTOR_MAP: dict[str, str] = {
    "005930": "semiconductor",  # 삼성전자
    "000660": "semiconductor",  # SK하이닉스
    "2330": "semiconductor",  # TSMC
    "NVDA": "semiconductor",
    "AMD": "semiconductor",
    "INTC": "semiconductor",
    "ASML": "semiconductor",
    "035420": "semiconductor",  # NAVER (반도체 아님 but IT)
    "207940": "biotech",  # 삼성바이오로직스
    "068270": "biotech",  # 셀트리온
    "196170": "biotech",  # 알테오젠
    "MRNA": "biotech",
    "PFE": "biotech",
    "055550": "finance",  # 신한지주
    "139130": "finance",  # DGB금융지주
    "JPM": "finance",
    "BAC": "finance",
}


def resolve_sector_template(asset: dict[str, Any]) -> SectorPromptTemplate:
    """Resolve sector template from asset symbol.

    v1: symbol prefix heuristic. Future: sector column in assets table.
    """
    symbol = str(asset.get("symbol") or "")
    # Strip exchange suffix (005930.KS → 005930)
    base_symbol = symbol.split(".")[0]
    sector_key = _SYMBOL_SECTOR_MAP.get(base_symbol) or _SYMBOL_SECTOR_MAP.get(symbol)
    if sector_key is None:
        return SECTOR_TEMPLATES["default"]
    return SECTOR_TEMPLATES.get(sector_key, SECTOR_TEMPLATES["default"])
