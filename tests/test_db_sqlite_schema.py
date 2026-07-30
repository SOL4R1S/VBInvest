"""Tests for scripts.lib.db_sqlite_schema — schema DDL validity."""

import sqlite3

from scripts.lib.db_sqlite_schema import SQLITE_SCHEMA


class TestSQLiteSchema:
    def test_schema_executes_without_error(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SQLITE_SCHEMA)
        conn.close()

    def test_schema_is_idempotent(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SQLITE_SCHEMA)
        conn.executescript(SQLITE_SCHEMA)  # second run should not fail
        conn.close()

    def test_expected_tables_created(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SQLITE_SCHEMA)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        expected = {
            "profiles",
            "assets",
            "watchlists",
            "watchlist_members",
            "daily_prices",
            "indicators",
            "news_items",
            "disclosures",
            "report_runs",
            "research_views",
            "settings_metadata",
            "job_locks",
            "portfolio_holdings",
        }
        for table in expected:
            assert table in tables, f"missing table: {table}"
        conn.close()

    def test_foreign_keys_valid(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SQLITE_SCHEMA)
        # Verify FK integrity
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert violations == []
        conn.close()

    def test_schema_contains_indexes(self):
        # Schema should include CREATE INDEX statements for performance
        assert "CREATE INDEX" in SQLITE_SCHEMA or "CREATE UNIQUE INDEX" in SQLITE_SCHEMA
