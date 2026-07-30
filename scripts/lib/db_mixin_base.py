"""Base class for DB mixins — declares cross-mixin interface for mypy."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3


class DBMixinBase:
    """Shared interface that all DB mixins can rely on at type-check time.

    Concrete implementations (VBinvestDB, SQLiteVBinvestDB) provide the real
    bodies via MRO; the stubs here exist solely so mypy can resolve
    ``self.connect()``, ``self._to_db_date()`` etc. inside mixin methods.
    """

    # -- connection ----------------------------------------------------------
    def connect(self) -> AbstractContextManager[sqlite3.Connection]:
        raise NotImplementedError

    # -- value coercion (from SQLiteValueMixin) ------------------------------
    def _to_db_date(self, value: Any) -> str | Any:
        raise NotImplementedError

    def _to_db_timestamp(self, value: Any) -> str | Any:
        raise NotImplementedError

    def _coerce_datetime(self, value: Any) -> datetime | None:
        raise NotImplementedError

    # -- identity helpers (from SQLiteIdentityMixin) -------------------------
    def _ensure_profile(self, auth_user_id: str, email: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    # -- cross-mixin queries -------------------------------------------------
    def fetch_watchlist_assets(self, slug: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_latest_research_views(self, slug: str) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    def fetch_recent_news_for_asset(self, asset_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_recent_disclosures_for_asset(self, asset_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError

    # -- settings metadata ---------------------------------------------------
    _settings_metadata_ready: bool
