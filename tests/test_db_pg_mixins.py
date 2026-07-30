"""Tests for PostgreSQL DB mixins — EntitlementMixin, IngestMixin, UserMixin.

Uses mock cursor/connection since PostgreSQL is not available in CI.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from scripts.lib.db_entitlement import EntitlementMixin
from scripts.lib.db_ingest import IngestMixin
from scripts.lib.db_user import UserMixin


class FakePGMixin:
    """Base that provides a mock connect() returning (conn, cursor) context managers."""

    def __init__(self):
        self._mock_cursor = MagicMock()
        self._mock_conn = MagicMock()
        self._mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self._mock_cursor)
        self._mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self._mock_conn.__enter__ = MagicMock(return_value=self._mock_conn)
        self._mock_conn.__exit__ = MagicMock(return_value=False)

    def connect(self):
        return self._mock_conn


class FakeEntitlementDB(FakePGMixin, EntitlementMixin):
    def _ensure_profile(self, conn, auth_user_id: str) -> int:
        return 1


class FakeIngestDB(FakePGMixin, IngestMixin):
    _settings_metadata_ready = True


class FakeUserDB(FakePGMixin, UserMixin):
    pass


class TestEntitlementMixin:
    def test_user_has_entitlement_true(self):
        db = FakeEntitlementDB()
        db._mock_cursor.fetchone.return_value = (1,)
        assert db.user_has_research_entitlement("user-1", "AAPL") is True

    def test_user_has_entitlement_false(self):
        db = FakeEntitlementDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.user_has_research_entitlement("user-1", "AAPL") is False

    def test_grant_ad_unlock(self):
        db = FakeEntitlementDB()
        db._mock_cursor.fetchone.return_value = (1,)
        result = db.grant_ad_unlock("user-1", "AAPL", "ad-event-1")
        assert result["unlocked"] is True

    def test_grant_subscription_entitlement(self):
        db = FakeEntitlementDB()
        db._mock_cursor.fetchone.return_value = (1,)
        result = db.grant_subscription_entitlement("user-1", "stripe", "sub-123")
        assert result["granted"] is True


class TestIngestMixin:
    def test_try_acquire_job_lock_success(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = ("lock-1",)
        assert db.try_acquire_job_lock("lock-1", "holder-a", 60) is True

    def test_try_acquire_job_lock_fail(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.try_acquire_job_lock("lock-1", "holder-a", 60) is False

    def test_release_job_lock(self):
        db = FakeIngestDB()
        db.release_job_lock("lock-1", "holder-a")
        db._mock_cursor.execute.assert_called_once()

    def test_fetch_setting_found(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = ("some-value",)
        assert db.fetch_setting("key-1") == "some-value"

    def test_fetch_setting_not_found(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.fetch_setting("key-1") is None

    def test_upsert_setting(self):
        db = FakeIngestDB()
        db.upsert_setting("key-1", "value-1")
        db._mock_cursor.execute.assert_called_once()

    def test_upsert_news_items_empty(self):
        db = FakeIngestDB()
        assert db.upsert_news_items([]) == 0

    def test_upsert_disclosures_empty(self):
        db = FakeIngestDB()
        assert db.upsert_disclosures([]) == 0

    def test_fetch_latest_report_run_found(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = (
            "run-1",
            "weekly",
            "watchlist",
            "default",
            "2026-01-15",
            "success",
            None,
            None,
            None,
            None,
        )
        result = db.fetch_latest_report_run("weekly", "default")
        assert result is not None
        assert result["run_id"] == "run-1"

    def test_fetch_latest_report_run_not_found(self):
        db = FakeIngestDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.fetch_latest_report_run("weekly", "default") is None


class TestUserMixin:
    def test_fetch_profile_found(self):
        db = FakeUserDB()
        db._mock_cursor.fetchone.return_value = (1, "user-1", "user-1-slug", "Test", "test@example.com", "local")
        result = db.fetch_profile_by_auth_user("user-1")
        assert result is not None
        assert result["profile_id"] == 1
        assert result["slug"] == "user-1-slug"

    def test_fetch_profile_not_found(self):
        db = FakeUserDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.fetch_profile_by_auth_user("user-1") is None

    def test_ensure_profile_for_auth_user(self):
        db = FakeUserDB()
        db._mock_cursor.fetchone.return_value = (1, "user-1", "user-1-slug", "test", "test@example.com", "local")
        result = db.ensure_profile_for_auth_user("user-1", "test@example.com")
        assert result["profile_id"] == 1

    def test_watchlist_slug_deterministic(self):
        db = FakeUserDB()
        slug1 = db._watchlist_slug("user-1", "My List")
        slug2 = db._watchlist_slug("user-1", "My List")
        assert slug1 == slug2

    def test_watchlist_slug_different_names(self):
        db = FakeUserDB()
        slug1 = db._watchlist_slug("user-1", "List A")
        slug2 = db._watchlist_slug("user-1", "List B")
        assert slug1 != slug2
