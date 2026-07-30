"""Tests for scripts.lib.db_mixin_base — abstract interface stubs."""

import pytest

from scripts.lib.db_mixin_base import DBMixinBase


class TestDBMixinBase:
    def test_connect_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base.connect()

    def test_to_db_date_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base._to_db_date("2024-01-01")

    def test_to_db_timestamp_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base._to_db_timestamp("2024-01-01T00:00:00")

    def test_coerce_datetime_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base._coerce_datetime("2024-01-01")

    def test_ensure_profile_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base._ensure_profile(None, "user-1")

    def test_fetch_watchlist_assets_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base.fetch_watchlist_assets("test-slug")

    def test_fetch_latest_research_views_raises(self):
        base = DBMixinBase()
        with pytest.raises(NotImplementedError):
            base.fetch_latest_research_views("test-slug")
