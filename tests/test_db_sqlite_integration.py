"""Integration tests for SQLiteVBinvestDB — real SQLite via tmp_path."""

import pytest

from scripts.lib.db_sqlite import SQLiteVBinvestDB


@pytest.fixture()
def db(tmp_path):
    return SQLiteVBinvestDB(tmp_path / "test.db")


class TestSQLiteVBinvestDB:
    def test_creates_database_file(self, tmp_path):
        path = tmp_path / "sub" / "test.db"
        SQLiteVBinvestDB(path)
        assert path.exists()

    def test_connect_returns_connection(self, db):
        conn = db.connect()
        assert conn is not None
        # row_factory should be set
        assert conn.row_factory is not None
        conn.close()

    def test_schema_tables_exist(self, db):
        with db.connect() as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "profiles" in tables
        assert "assets" in tables
        assert "watchlists" in tables
        assert "watchlist_members" in tables
        assert "daily_prices" in tables
        assert "news_items" in tables
        assert "report_runs" in tables

    def test_foreign_keys_enabled(self, db):
        with db.connect() as conn:
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            assert result[0] == 1


class TestSQLiteIdentity:
    def test_ensure_profile_creates_new(self, db):
        profile = db.ensure_profile_for_auth_user("user-1", "test@example.com")
        assert profile["auth_user_id"] == "user-1"
        assert profile["email"] == "test@example.com"
        assert profile["slug"]  # non-empty

    def test_ensure_profile_idempotent(self, db):
        p1 = db.ensure_profile_for_auth_user("user-1", "a@b.com")
        p2 = db.ensure_profile_for_auth_user("user-1", "a@b.com")
        assert p1["profile_id"] == p2["profile_id"]

    def test_fetch_profile_by_auth_user(self, db):
        db.ensure_profile_for_auth_user("user-2", "x@y.com")
        profile = db.fetch_profile_by_auth_user("user-2")
        assert profile is not None
        assert profile["auth_user_id"] == "user-2"

    def test_fetch_profile_not_found(self, db):
        assert db.fetch_profile_by_auth_user("nonexistent") is None

    def test_ensure_assets_for_refresh(self, db):
        assets = [
            {"symbol": "nvda", "display_name_ko": "엔비디아", "exchange": "NASDAQ", "currency": "USD"},
            {"symbol": "005930", "display_name_ko": "삼성전자", "exchange": "KRX", "currency": "KRW"},
        ]
        result = db.ensure_assets_for_refresh(assets)
        assert len(result) == 2
        assert result[0]["symbol"] == "NVDA"  # uppercased
        assert result[0]["asset_id"] > 0
        assert result[1]["symbol"] == "005930"

    def test_ensure_assets_empty(self, db):
        assert db.ensure_assets_for_refresh([]) == []

    def test_ensure_assets_skips_empty_symbol(self, db):
        result = db.ensure_assets_for_refresh([{"symbol": ""}, {"symbol": "  "}])
        assert result == []

    def test_create_and_list_watchlist(self, db):
        db.ensure_assets_for_refresh([{"symbol": "AAPL"}])
        wl = db.create_user_watchlist("user-1", "My List", ["AAPL"])
        assert wl["name"] == "My List"
        assert "AAPL" in wl.get("symbols", [])

        lists = db.list_user_watchlists("user-1")
        assert len(lists) == 1
        assert lists[0]["name"] == "My List"

    def test_fetch_watchlist_assets(self, db):
        db.ensure_assets_for_refresh([{"symbol": "TSLA", "display_name_ko": "테슬라"}])
        db.create_user_watchlist("user-1", "EV", ["TSLA"])
        # Need the slug
        lists = db.list_user_watchlists("user-1")
        slug = lists[0]["slug"]
        assets = db.fetch_watchlist_assets(slug)
        assert len(assets) == 1
        assert assets[0]["symbol"] == "TSLA"


class TestSQLiteSources:
    def test_upsert_news_items_empty(self, db):
        assert db.upsert_news_items([]) == 0

    def test_upsert_news_items(self, db):
        assets = db.ensure_assets_for_refresh([{"symbol": "AAPL"}])
        asset_id = assets[0]["asset_id"]
        rows = [
            {
                "provider": "test",
                "source": "rss",
                "source_id": "news-1",
                "url": "https://example.com/1",
                "canonical_url": None,
                "title": "Test News",
                "published_at": "2024-01-01T00:00:00Z",
                "content_hash": "abc123",
                "language": "en",
                "summary": "A test article",
                "raw_json": {"foo": "bar"},
                "asset_id": asset_id,
            },
        ]
        count = db.upsert_news_items(rows)
        assert count == 1

    def test_upsert_news_items_dedup_by_source_id(self, db):
        assets = db.ensure_assets_for_refresh([{"symbol": "TSLA"}])
        asset_id = assets[0]["asset_id"]
        row = {
            "provider": "test",
            "source": "rss",
            "source_id": "dup-1",
            "url": "https://example.com/1",
            "canonical_url": None,
            "title": "Original",
            "published_at": "2024-01-01T00:00:00Z",
            "content_hash": "hash1",
            "language": "en",
            "summary": "First",
            "raw_json": None,
            "asset_id": asset_id,
        }
        db.upsert_news_items([row])
        row["title"] = "Updated"
        db.upsert_news_items([row])
        # Should still be 1 row (upsert)
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
        assert count == 1


class TestSQLiteReports:
    def test_record_report_run(self, db):
        run_id = db.record_report_run(
            run_type="daily",
            status="completed",
            scope_slug="semiconductor-core",
        )
        assert run_id  # non-empty UUID string
        assert len(run_id) == 36  # UUID format

    def test_record_report_run_with_error(self, db):
        run_id = db.record_report_run(
            run_type="on_demand",
            status="failed",
            error_message="AI provider timeout",
            failed_assets=["NVDA"],
        )
        assert run_id

    def test_fetch_latest_research_views_empty(self, db):
        result = db.fetch_latest_research_views("nonexistent")
        assert result == {}
