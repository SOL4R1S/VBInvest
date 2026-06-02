from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.lib.db import build_indicator_rows, build_price_rows
from scripts.lib.db_sqlite import SQLiteVBinvestDB
from scripts.lib.obsidian import GENERATED_MARKER, note_path


def _seed_sqlite_asset(repo: SQLiteVBinvestDB) -> None:
    repo.ensure_profile_for_auth_user("user-a", "user-a@example.com")
    watchlist = repo.create_user_watchlist("user-a", "핵심", ["NVDA"])
    asset_id = repo.fetch_watchlist_assets(watchlist["slug"])[0]["asset_id"]
    prices = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000, "source": "yfinance"},
            {"date": date(2026, 6, 2), "open": 104, "high": 110, "low": 103, "close": 108, "volume": 1200, "source": "yfinance"},
        ]
    )
    indicators = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "return_1d": 0.01, "return_1m": 0.05, "ma5": 101, "ma20": 100, "ma50": 99, "ma120": 95, "rsi14": 58},
            {"date": date(2026, 6, 2), "return_1d": 0.04, "return_1m": 0.12, "ma5": 103, "ma20": 101, "ma50": 99, "ma120": 95, "rsi14": 62},
        ]
    )
    repo.upsert_prices(build_price_rows(asset_id, prices))
    repo.upsert_indicators(build_indicator_rows(asset_id, indicators))


def test_sqlite_on_demand_report_writes_research_run_and_obsidian_note(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_sqlite_asset(repo)

    row = repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)

    assert row["target_slug"] == "NVDA"
    assert row["opinion"] in {"매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"}
    assert row["run_id"]
    assert row["obsidian_path"]
    note = Path(row["obsidian_path"])
    assert note.exists()
    assert GENERATED_MARKER in note.read_text(encoding="utf-8")
    assert "Disclaimer" in note.read_text(encoding="utf-8")

    latest_run = repo.fetch_latest_report_run("on-demand-research", "NVDA")
    assert latest_run is not None
    assert latest_run["status"] == "ok"
    assert latest_run["output_path"] == str(note)
    latest = repo.fetch_latest_research_for_asset("NVDA")
    assert latest is not None
    assert latest["sources"][0]["kind"] == "source_gap"


def test_sqlite_on_demand_report_failure_records_run_and_preserves_previous_report(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_sqlite_asset(repo)
    previous = repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)
    note = note_path(vault, "NVDA", previous["report_date"])
    note.write_text("# manual note\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Obsidian export failed"):
        repo.generate_research_for_asset("user-a", "NVDA", obsidian_vault_path=vault)

    latest = repo.fetch_latest_research_for_asset("NVDA")
    assert latest is not None
    assert latest["thesis"] == previous["thesis"]
    failed_run = repo.fetch_latest_report_run("on-demand-research", "NVDA")
    assert failed_run is not None
    assert failed_run["status"] == "failed"
    assert failed_run["error_message"] == "Obsidian export failed"


def test_sqlite_report_run_cancel_updates_running_job(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    run_id = repo.record_report_run(
        run_type="on-demand-research",
        status="running",
        scope_type="asset",
        scope_slug="NVDA",
        failed_assets=[],
        output_summary="started",
    )

    canceled = repo.cancel_report_run(run_id)

    assert canceled is not None
    assert canceled["run_id"] == run_id
    assert canceled["status"] == "canceled"
    assert canceled["error_message"] == "canceled by user"


def test_sqlite_report_run_cancel_updates_queued_job(tmp_path: Path) -> None:
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")
    run_id = repo.record_report_run(
        run_type="on-demand-research",
        status="queued",
        scope_type="asset",
        scope_slug="NVDA",
        failed_assets=[],
        output_summary="queued",
    )

    canceled = repo.cancel_report_run(run_id)

    assert canceled is not None
    assert canceled["run_id"] == run_id
    assert canceled["status"] == "canceled"
    assert canceled["error_message"] == "canceled by user"
