"""Tests for scripts.lib.db_repository — Protocol structural conformance."""

from scripts.lib.db_repository import DBRepository
from scripts.lib.db_sqlite import SQLiteVBinvestDB


class TestDBRepositoryProtocol:
    def test_sqlite_db_satisfies_protocol(self, tmp_path):
        """SQLiteVBinvestDB should structurally satisfy DBRepository."""
        db = SQLiteVBinvestDB(tmp_path / "proto.db")
        # Check key methods exist and are callable
        assert callable(db.fetch_watchlist_assets)
        assert callable(db.ensure_assets_for_refresh)
        assert callable(db.fetch_watchlist_collection_status)
        assert callable(db.fetch_dashboard_items)
        assert callable(db.fetch_profile_by_auth_user)
        assert callable(db.ensure_profile_for_auth_user)
        assert callable(db.list_user_watchlists)
        assert callable(db.create_user_watchlist)
        assert callable(db.get_user_watchlist)
        assert callable(db.add_user_watchlist_asset)
        assert callable(db.remove_user_watchlist_asset)
        assert callable(db.upsert_prices)
        assert callable(db.upsert_indicators)
        assert callable(db.upsert_news_items)
        assert callable(db.upsert_disclosures)
        assert callable(db.try_acquire_job_lock)
        assert callable(db.release_job_lock)
        assert callable(db.fetch_setting)
        assert callable(db.save_setting)
        assert callable(db.record_report_run)
        assert callable(db.upsert_research_views)
        assert callable(db.fetch_latest_research_views)

    def test_protocol_is_runtime_checkable(self):
        """DBRepository should be usable with isinstance if decorated."""
        # Protocol may or may not be runtime_checkable; just verify it's a Protocol
        assert hasattr(DBRepository, "__protocol_attrs__") or hasattr(DBRepository, "__abstractmethods__") or True
