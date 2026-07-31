from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class DBRepository(Protocol):
    def fetch_watchlist_assets(self, slug: str) -> list[dict[str, Any]]: ...

    def ensure_assets_for_refresh(self, assets: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

    def fetch_watchlist_collection_status(self, slug: str) -> list[dict[str, Any]]: ...

    def fetch_dashboard_items(self, slug: str, *, days: int = 1260) -> list[dict[str, Any]]: ...

    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None: ...

    def ensure_profile_for_auth_user(self, auth_user_id: str, email: str | None) -> dict[str, Any]: ...

    def list_user_watchlists(self, auth_user_id: str) -> list[dict[str, Any]]: ...

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]) -> dict[str, Any]: ...

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str) -> dict[str, Any] | None: ...

    def add_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str) -> dict[str, Any] | None: ...

    def remove_user_watchlist_asset(
        self, auth_user_id: str, watchlist_id: str, symbol: str
    ) -> dict[str, Any] | None: ...

    def upsert_prices(self, rows: list[dict[str, Any]]) -> int: ...

    def upsert_indicators(self, rows: list[dict[str, Any]]) -> int: ...

    def list_daily_indicators(self, auth_user_id: str, *, limit: int = 50) -> list[dict[str, Any]]: ...

    def fetch_watchlist_price_history(
        self, auth_user_id: str, slug: str, *, days: int = 365
    ) -> list[dict[str, Any]]: ...

    def upsert_news_items(self, rows: list[dict[str, Any]]) -> int: ...

    def upsert_disclosures(self, rows: list[dict[str, Any]]) -> int: ...

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool: ...

    def release_job_lock(self, lock_name: str, holder: str) -> None: ...

    def fetch_setting(self, key: str) -> str | None: ...

    def upsert_setting(self, key: str, value: str) -> None: ...

    def record_report_run(self, **kwargs: object) -> str: ...

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None: ...

    def fetch_latest_successful_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None: ...

    def fetch_latest_price_dates(self, asset_ids: list[int]) -> dict[int, date]: ...

    def fetch_price_date_ranges(self, asset_ids: list[int]) -> dict[int, dict[str, date]]: ...

    def upsert_research_views(self, rows: list[dict[str, Any]]) -> int: ...

    def fetch_latest_research_views(self, slug: str) -> dict[str, dict[str, Any]]: ...

    def fetch_latest_research_for_asset(self, symbol: str) -> dict[str, Any] | None: ...

    def generate_research_for_asset(
        self,
        auth_user_id: str,
        symbol: str,
        *,
        obsidian_vault_path: str | None = None,
    ) -> dict[str, Any]: ...

    def cancel_report_run(self, run_id: str) -> dict[str, Any] | None: ...

    # Portfolio holdings
    def list_user_portfolio_holdings(self, auth_user_id: str) -> list[dict[str, Any]]: ...

    def create_user_portfolio_holding(
        self,
        auth_user_id: str,
        symbol: str,
        quantity: float,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any]: ...

    def update_user_portfolio_holding(
        self,
        auth_user_id: str,
        holding_id: str,
        quantity: float | None,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any] | None: ...

    def delete_user_portfolio_holding(self, auth_user_id: str, holding_id: str) -> bool: ...

    # Portfolio transactions
    def list_portfolio_transactions(
        self,
        auth_user_id: str,
        *,
        holding_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def create_portfolio_transaction(
        self,
        auth_user_id: str,
        holding_id: str,
        transaction_type: str,
        quantity: float,
        price_per_unit: float,
        fee: float,
        transaction_date: str,
        note: str | None,
    ) -> dict[str, Any]: ...

    # Portfolio returns
    def fetch_portfolio_returns(
        self,
        auth_user_id: str,
        *,
        days: int = 365,
    ) -> dict[str, Any]: ...

    def upsert_portfolio_snapshot(
        self,
        auth_user_id: str,
        snapshot_date: str,
        total_cost: float,
        total_value: float,
        total_return: float,
        total_return_pct: float,
        daily_return_pct: float | None,
        holdings_json: str,
    ) -> None: ...

    def fetch_portfolio_snapshots(
        self,
        auth_user_id: str,
        *,
        days: int = 365,
    ) -> list[dict[str, Any]]: ...

    # Notifications
    def list_notifications(
        self,
        auth_user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...

    def create_notification(
        self,
        auth_user_id: str,
        notification_type: str,
        title: str,
        body: str,
        metadata: str | None = None,
    ) -> dict[str, Any]: ...

    def mark_notification_read(self, auth_user_id: str, notification_id: str) -> bool: ...

    def mark_all_notifications_read(self, auth_user_id: str) -> int: ...

    # Alert rules
    def list_alert_rules(
        self,
        auth_user_id: str,
        *,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]: ...

    def create_alert_rule(
        self,
        auth_user_id: str,
        symbol: str,
        condition: str,
        threshold: float,
    ) -> dict[str, Any]: ...

    def update_alert_rule(
        self,
        auth_user_id: str,
        rule_id: str,
        *,
        enabled: bool | None = None,
        threshold: float | None = None,
    ) -> bool: ...

    def delete_alert_rule(self, auth_user_id: str, rule_id: str) -> bool: ...

    def touch_alert_rule_triggered(self, auth_user_id: str, rule_id: str) -> None: ...
