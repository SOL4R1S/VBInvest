from pathlib import Path

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.indicators import add_indicators
from scripts.lib.prices import synthetic_history
from scripts.lib.watchlists import SEMICONDUCTOR_CORE
from scripts.lib.validate import validate_html


def test_render_dashboard_contains_required_chart_hooks_and_labels():
    data = []
    for asset in SEMICONDUCTOR_CORE[:2]:
        frame = add_indicators(synthetic_history(asset["symbol"], days=140))
        data.append({"asset": asset, "history": frame})

    html = render_dashboard_html(data, title="Test Dashboard")

    assert "function pointsFor" in html
    assert "function render" in html
    assert "setPolyline" in html
    assert "function shiftWindow" in html
    assert "pointerdown" in html
    assert "addEventListener('wheel'" in html
    assert "줌 초기화" in html
    assert "캔들" in html
    assert "data-mode=\"candle\"" in html
    assert "renderCandles" in html
    assert "candle-up" in html
    assert "200일선" not in html
    assert "엔비디아" not in html  # only first two fallback assets in this test


def test_render_dashboard_includes_on_demand_research_sections():
    frame = add_indicators(synthetic_history("NVDA", days=140))
    html = render_dashboard_html(
        [{
            "asset": {"symbol": "NVDA", "display_name_ko": "엔비디아"},
            "history": frame,
            "opinion": "아웃퍼폼",
            "thesis": "AI 수요가 강하지만 가격 리스크는 관리한다.",
            "rationale": ["모멘텀 양호", "RSI 중립"],
            "risks": ["가이던스 리스크"],
            "triggers": ["실적 발표"],
        }],
        title="Research Test",
    )

    assert "research-detail: NVDA start" in html
    assert "리서치 의견" in html
    assert "AI 수요가 강하지만 가격 리스크는 관리한다." in html
    assert "아웃퍼폼" in html


def test_validate_html_accepts_rendered_dashboard(tmp_path: Path):
    frame = add_indicators(synthetic_history("NVDA", days=140))
    html = render_dashboard_html(
        [{"asset": {"symbol": "NVDA", "display_name_ko": "엔비디아"}, "history": frame}],
        title="Validation Test",
    )
    target = tmp_path / "latest.html"
    target.write_text(html, encoding="utf-8")

    result = validate_html(target)

    assert result.ok
    assert not result.errors
