from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from scripts.lib.db import VBinvestDB, build_indicator_rows, build_price_rows
from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.db_sqlite import SQLiteVBinvestDB


def _write_config(config_path: Path, *, mode: str, sqlite_path: Path, postgres_url: str = "") -> None:
    config_path.write_text(
        "\n".join(
            [
                "first_run_completed = true",
                "[database]",
                f'mode = "{mode}"',
                f'sqlite_path = "{sqlite_path}"',
                f'postgres_url = "{postgres_url}"',
            ]
        ),
        encoding="utf-8",
    )


def test_sqlite_mode_bootstraps_temp_db_with_core_tables(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    sqlite_path = tmp_path / "data" / "vbinvest.sqlite3"
    _write_config(config_path, mode="sqlite", sqlite_path=sqlite_path)

    repo = build_database_from_local_config(config_path=config_path, environ={})

    assert isinstance(repo, SQLiteVBinvestDB)
    assert sqlite_path.exists()
    with sqlite3.connect(sqlite_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "profiles",
        "assets",
        "watchlists",
        "watchlist_members",
        "daily_prices",
        "daily_indicators",
        "news_items",
        "disclosures",
        "research_views",
        "report_runs",
        "settings_metadata",
    }.issubset(tables)


def test_shared_repository_roundtrip_works_for_sqlite_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    sqlite_path = tmp_path / "data" / "vbinvest.sqlite3"
    _write_config(config_path, mode="sqlite", sqlite_path=sqlite_path)
    repo = build_database_from_local_config(config_path=config_path, environ={})

    profile = repo.ensure_profile_for_auth_user("user-1", "user-1@example.com")
    fetched_profile = repo.fetch_profile_by_auth_user("user-1")
    assert profile["auth_user_id"] == "user-1"
    assert fetched_profile is not None
    assert fetched_profile["auth_user_id"] == "user-1"

    created = repo.create_user_watchlist("user-1", "핵심", ["NVDA", "TSM"])
    listed = repo.list_user_watchlists("user-1")
    assert listed and listed[0]["symbols"] == ["NVDA", "TSM"]
    assert created["slug"]

    price_frame = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000, "source": "yfinance"},
            {"date": date(2026, 6, 2), "open": 101, "high": 105, "low": 100, "close": 104, "volume": 1200, "source": "yfinance"},
        ]
    )
    indicator_frame = pd.DataFrame(
        [
            {"date": date(2026, 6, 1), "return_1d": 0.01, "ma5": 100.5, "ma20": 98.2, "ma50": 95.5, "ma120": 91.0, "rsi14": 61.0},
            {"date": date(2026, 6, 2), "return_1d": 0.03, "ma5": 101.2, "ma20": 98.9, "ma50": 95.8, "ma120": 91.1, "rsi14": 64.1},
        ]
    )
    asset_id = repo.fetch_watchlist_assets(created["slug"])[0]["asset_id"]
    assert repo.upsert_prices(build_price_rows(asset_id, price_frame)) == 2
    assert repo.upsert_indicators(build_indicator_rows(asset_id, indicator_frame)) == 2
    collection_status = repo.fetch_watchlist_collection_status(created["slug"])
    assert collection_status == [
        {
            "symbol": "NVDA",
            "display_name_ko": None,
            "exchange": None,
            "provider": "yfinance",
            "latest_price_date": date(2026, 6, 2),
            "latest_fetched_at": collection_status[0]["latest_fetched_at"],
            "price_rows": 2,
            "indicator_rows": 2,
            "has_synthetic": False,
            "status": "collected",
        },
        {
            "symbol": "TSM",
            "display_name_ko": None,
            "exchange": None,
            "provider": None,
            "latest_price_date": None,
            "latest_fetched_at": None,
            "price_rows": 0,
            "indicator_rows": 0,
            "has_synthetic": False,
            "status": "missing",
        },
    ]

    run_id = repo.record_report_run(
        run_type="startup-market-refresh",
        status="ok",
        scope_type="watchlist",
        scope_slug=created["slug"],
        failed_assets=[],
        output_summary="ok",
        output_path="/tmp/report.md",
    )
    latest_run = repo.fetch_latest_report_run("startup-market-refresh", created["slug"])
    assert latest_run is not None
    assert latest_run["run_id"] == run_id
    assert latest_run["status"] == "ok"

    research_row = {
        "target_type": "asset",
        "target_slug": "NVDA",
        "report_date": date(2026, 6, 2),
        "horizon": "on_demand",
        "opinion": "중립",
        "thesis": "테스트",
        "rationale": ["근거"],
        "bull": "bull",
        "base": "base",
        "bear": "bear",
        "risks": ["risk"],
        "triggers": ["trigger"],
        "sources": [{"type": "db"}],
        "confidence": 0.6,
        "source_freshness_status": "fresh",
        "access_tier": "free",
    }
    assert repo.upsert_research_views([research_row]) == 1
    latest_research = repo.fetch_latest_research_for_asset("NVDA")
    assert latest_research is not None
    assert latest_research["target_slug"] == "NVDA"
    assert latest_research["opinion"] == "중립"
    assert latest_research["risks"] == ["risk"]
    assert latest_research["sources"] == [{"type": "db"}]


def test_postgres_url_mode_preserves_existing_postgres_path(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    sqlite_path = tmp_path / "data" / "vbinvest.sqlite3"
    _write_config(
        config_path,
        mode="postgres_url",
        sqlite_path=sqlite_path,
        postgres_url="postgresql://alice:secret@127.0.0.1:6543/mydb",
    )

    repo = build_database_from_local_config(config_path=config_path, environ={})

    assert isinstance(repo, VBinvestDB)
    assert repo.config.host == "127.0.0.1"
    assert repo.config.port == 6543
    assert repo.config.database == "mydb"
    assert repo.config.user == "alice"
    assert repo.config.password == "secret"
    assert repo.config.dsn() == "postgresql://alice:***@127.0.0.1:6543/mydb"
