"""Integration tests for SQLiteReportsMixin — report runs, research views, obsidian exports."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.db_sqlite import SQLiteVBinvestDB


@pytest.fixture()
def db(tmp_path: Path) -> SQLiteVBinvestDB:
    return SQLiteVBinvestDB(tmp_path / "test.db")


@pytest.fixture()
def asset_id(db: SQLiteVBinvestDB) -> int:
    assets = db.ensure_assets_for_refresh([{"symbol": "AAPL", "display_name_ko": "애플"}])
    return assets[0]["asset_id"]


class TestCancelReportRun:
    def test_cancel_queued_run(self, db: SQLiteVBinvestDB):
        run_id = db.record_report_run(run_type="weekly", status="queued")
        result = db.cancel_report_run(run_id)
        assert result is not None
        assert result["status"] == "canceled"
        assert result["error_message"] == "canceled by user"

    def test_cancel_running_run(self, db: SQLiteVBinvestDB):
        run_id = db.record_report_run(run_type="weekly", status="running")
        result = db.cancel_report_run(run_id)
        assert result is not None
        assert result["status"] == "canceled"

    def test_cancel_completed_run_noop(self, db: SQLiteVBinvestDB):
        run_id = db.record_report_run(run_type="weekly", status="success")
        result = db.cancel_report_run(run_id)
        assert result is not None
        assert result["status"] == "success"  # unchanged

    def test_cancel_nonexistent_run(self, db: SQLiteVBinvestDB):
        result = db.cancel_report_run("nonexistent-id")
        assert result is None


class TestFetchLatestSuccessfulReportRun:
    def test_returns_only_successful(self, db: SQLiteVBinvestDB):
        db.record_report_run(run_type="weekly", status="failed", scope_slug="default")
        db.record_report_run(run_type="weekly", status="success", scope_slug="default")
        result = db.fetch_latest_successful_report_run("weekly", "default")
        assert result is not None
        assert result["status"] == "success"

    def test_skips_failed_and_running(self, db: SQLiteVBinvestDB):
        db.record_report_run(run_type="weekly", status="success", scope_slug="default")
        db.record_report_run(run_type="weekly", status="failed", scope_slug="default")
        db.record_report_run(run_type="weekly", status="running", scope_slug="default")
        result = db.fetch_latest_successful_report_run("weekly", "default")
        assert result is not None
        assert result["status"] == "success"

    def test_none_when_no_successful(self, db: SQLiteVBinvestDB):
        db.record_report_run(run_type="weekly", status="failed", scope_slug="default")
        result = db.fetch_latest_successful_report_run("weekly", "default")
        assert result is None

    def test_none_when_empty(self, db: SQLiteVBinvestDB):
        result = db.fetch_latest_successful_report_run("weekly", "default")
        assert result is None


class TestUpsertResearchViews:
    def test_empty(self, db: SQLiteVBinvestDB):
        assert db.upsert_research_views([]) == 0

    def test_insert_single(self, db: SQLiteVBinvestDB):
        rows = [
            {
                "target_type": "asset",
                "target_slug": "AAPL",
                "report_date": "2026-01-15",
                "horizon": "on_demand",
                "opinion": "bullish",
                "thesis": "Strong earnings",
                "rationale": "AI growth",
                "bull": "AI capex cycle",
                "base": "Steady growth",
                "bear": "Regulation risk",
                "risks": ["regulation", "competition"],
                "triggers": ["earnings beat"],
                "sources": ["https://example.com"],
                "confidence": 0.8,
                "source_freshness_status": "fresh",
                "access_tier": "free",
            }
        ]
        assert db.upsert_research_views(rows) == 1

    def test_upsert_overwrites(self, db: SQLiteVBinvestDB):
        row = {
            "target_type": "asset",
            "target_slug": "AAPL",
            "report_date": "2026-01-15",
            "horizon": "on_demand",
            "opinion": "bullish",
            "thesis": "Original thesis",
            "rationale": "Rationale",
            "bull": "Bull case",
            "base": "Base case",
            "bear": "Bear case",
            "risks": [],
            "triggers": [],
            "sources": [],
            "confidence": 0.5,
            "source_freshness_status": "fresh",
            "access_tier": "free",
        }
        db.upsert_research_views([row])
        updated = {**row, "opinion": "bearish", "confidence": 0.3}
        db.upsert_research_views([updated])
        result = db.fetch_latest_research_for_asset("AAPL")
        assert result is not None
        assert result["opinion"] == "bearish"
        assert result["confidence"] == 0.3


class TestFetchLatestResearchForAsset:
    def test_not_found(self, db: SQLiteVBinvestDB):
        assert db.fetch_latest_research_for_asset("MSFT") is None

    def test_found(self, db: SQLiteVBinvestDB):
        db.upsert_research_views(
            [
                {
                    "target_type": "asset",
                    "target_slug": "AAPL",
                    "report_date": "2026-01-15",
                    "horizon": "on_demand",
                    "opinion": "neutral",
                    "thesis": "Wait and see",
                    "rationale": "Mixed signals",
                    "bull": "Services growth",
                    "base": "Flat",
                    "bear": "China slowdown",
                    "risks": ["china"],
                    "triggers": ["guidance"],
                    "sources": ["https://example.com/report"],
                    "confidence": 0.6,
                    "source_freshness_status": "fresh",
                    "access_tier": "free",
                }
            ]
        )
        result = db.fetch_latest_research_for_asset("AAPL")
        assert result is not None
        assert result["target_slug"] == "AAPL"
        assert result["opinion"] == "neutral"
        assert result["risks"] == ["china"]
        assert result["triggers"] == ["guidance"]
        assert result["sources"] == ["https://example.com/report"]

    def test_ignores_non_on_demand_horizon(self, db: SQLiteVBinvestDB):
        db.upsert_research_views(
            [
                {
                    "target_type": "asset",
                    "target_slug": "AAPL",
                    "report_date": "2026-01-15",
                    "horizon": "weekly",
                    "opinion": "bullish",
                    "thesis": "Weekly view",
                    "rationale": "R",
                    "bull": "B",
                    "base": "Ba",
                    "bear": "Be",
                    "risks": [],
                    "triggers": [],
                    "sources": [],
                    "confidence": 0.9,
                    "source_freshness_status": "fresh",
                    "access_tier": "free",
                }
            ]
        )
        result = db.fetch_latest_research_for_asset("AAPL")
        assert result is None  # weekly horizon not returned


class TestRecordObsidianExport:
    def test_record_new_export(self, db: SQLiteVBinvestDB):
        db.record_obsidian_export(
            export_id="export-1",
            view_id=None,
            target_slug="AAPL",
            report_date="2026-01-15",
            vault_path="/vault",
            relative_path="reports/AAPL.md",
            file_path="/vault/reports/AAPL.md",
            file_hash="abc123",
            status="success",
            error_message=None,
        )
        # Verify by fetching — no direct fetch method, so just ensure no error
        # and a second upsert works (idempotent)
        db.record_obsidian_export(
            export_id="export-2",
            view_id=None,
            target_slug="AAPL",
            report_date="2026-01-15",
            vault_path="/vault",
            relative_path="reports/AAPL.md",
            file_path="/vault/reports/AAPL.md",
            file_hash="def456",
            status="success",
            error_message=None,
        )

    def test_record_failed_export(self, db: SQLiteVBinvestDB):
        db.record_obsidian_export(
            export_id="export-3",
            view_id=None,
            target_slug="MSFT",
            report_date="2026-01-16",
            vault_path="/vault",
            relative_path="reports/MSFT.md",
            file_path="/vault/reports/MSFT.md",
            file_hash="ghi789",
            status="failed",
            error_message="disk full",
        )
