from datetime import date

import pytest

from scripts.lib.obsidian import ManualNoteError, export_research_rows, note_path, render_note, write_generated_note


def sample_row():
    return {
        "target_slug": "005930.KS",
        "report_date": date(2026, 6, 1),
        "opinion": "매수",
        "thesis": "삼성전자는 요청 기반 리서치 기준 점검 대상입니다.",
        "bull": "AI 메모리 수요 개선",
        "base": "가격·지표 기준 점검",
        "bear": "수요 둔화",
        "risks": '["실적 하향"]',
        "triggers": '["실적 발표"]',
        "metrics_snapshot": (
            '{"date":"2026-06-01","current_price":81200,"currency":"KRW",'
            '"return_1d":0.01,"return_1w":0.03,"return_1m":0.08,"return_3m":0.12,'
            '"rsi14":55.5,"volume":2200,"ma5":80800,"ma20":79900,"ma50":78500,"ma120":77100,'
            '"drawdown_52w":-0.08}'
        ),
        "target_price_summary": (
            '{"status":"found","target_price":95000,"currency":"KRW","implied_upside":0.1699507389,'
            '"source_title":"증권사 목표가 95,000원 제시"}'
        ),
        "sources": '[{"title":"Source","url":"https://example.com"}]',
        "run_id": "run-1",
    }


def test_export_path_sanitizes_ticker_symbol(tmp_path):
    path = note_path(tmp_path, "005930.KS", date(2026, 6, 1))

    assert path == tmp_path / "30 Projects" / "VBinvest" / "005930.KS" / "2026-06-01.md"


def test_render_note_contains_frontmatter_sources_and_backlink():
    markdown = render_note(sample_row())

    assert "ticker: 005930.KS" in markdown
    assert "opinion: 매수" in markdown
    assert "# 005930.KS On-Demand Research" in markdown
    assert "Weekly Research" not in markdown
    assert "[[VBinvest]]" in markdown
    assert "## Price / Target Snapshot" in markdown
    assert "Current price: 81,200 KRW" in markdown
    assert "Target price: 95,000 KRW" in markdown
    assert "Implied upside: +17.0%" in markdown
    assert "RSI14: 55.5" in markdown
    assert "https://example.com" in markdown
    assert "not investment advice" in markdown


def test_render_note_shows_ai_estimated_target_price():
    row = sample_row()
    row["target_price_summary"] = (
        '{"status":"estimated","target_price":91000,"currency":"KRW","implied_upside":0.1206896552,'
        '"source_title":"VBinvest AI-estimated target price","message":"외부 명시 목표가가 없어 자체 산정했습니다."}'
    )

    markdown = render_note(row)

    assert "Target price: 91,000 KRW" in markdown
    assert "Implied upside: +12.1%" in markdown
    assert "Target source: VBinvest AI-estimated target price" in markdown


def test_manual_note_without_marker_is_not_overwritten(tmp_path):
    path = note_path(tmp_path, "005930.KS", date(2026, 6, 1))
    path.parent.mkdir(parents=True)
    path.write_text("manual note", encoding="utf-8")

    with pytest.raises(ManualNoteError):
        write_generated_note(path, render_note(sample_row()))

    assert path.read_text(encoding="utf-8") == "manual note"


def test_export_records_db_status_ok(tmp_path):
    class FakeDB:
        def __init__(self):
            self.records = []

        def record_obsidian_export(self, **kwargs):
            self.records.append(kwargs)

    db = FakeDB()
    results = export_research_rows([sample_row()], tmp_path, db=db)

    assert results[0]["status"] == "ok"
    assert results[0]["path"].endswith("005930.KS/2026-06-01.md")
    assert db.records[0]["status"] == "ok"
    assert db.records[0]["file_path"].endswith("005930.KS/2026-06-01.md")
