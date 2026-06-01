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
    assert "[[VBinvest]]" in markdown
    assert "https://example.com" in markdown
    assert "not investment advice" in markdown


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
