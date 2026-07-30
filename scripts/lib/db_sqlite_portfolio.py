"""SQLitePortfolioMixin — portfolio holdings, transactions, snapshots CRUD."""

from __future__ import annotations

import json
import uuid
from typing import Any

from scripts.lib.db_mixin_base import DBMixinBase
from scripts.lib.portfolio_returns import compute_portfolio_returns


class SQLitePortfolioMixin(DBMixinBase):
    """portfolio_holdings, portfolio_transactions, portfolio_snapshots CRUD."""

    # -- holdings ---------------------------------------------------------------

    def list_user_portfolio_holdings(self, auth_user_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT h.holding_id, a.symbol, a.display_name_ko, a.currency,
                       h.quantity, h.average_cost, h.note
                FROM portfolio_holdings h
                JOIN profiles p ON p.profile_id = h.profile_id
                JOIN assets a ON a.asset_id = h.asset_id
                WHERE p.auth_user_id = ?
                ORDER BY a.symbol
                """,
                (auth_user_id,),
            ).fetchall()
        return [
            {
                "holding_id": row["holding_id"],
                "symbol": row["symbol"],
                "display_name_ko": row["display_name_ko"],
                "currency": row["currency"],
                "quantity": row["quantity"],
                "average_cost": row["average_cost"],
                "note": row["note"],
            }
            for row in rows
        ]

    def create_user_portfolio_holding(
        self,
        auth_user_id: str,
        symbol: str,
        quantity: float,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any]:
        holding_id = str(uuid.uuid4())
        with self.connect() as conn:
            profile = conn.execute("SELECT profile_id FROM profiles WHERE auth_user_id = ?", (auth_user_id,)).fetchone()
            asset = conn.execute(
                "SELECT asset_id, currency FROM assets WHERE symbol = ? AND active = 1", (symbol,)
            ).fetchone()
            if profile is None or asset is None:
                raise LookupError("profile or asset not found")
            conn.execute(
                """
                INSERT INTO portfolio_holdings
                  (holding_id, profile_id, asset_id, quantity, average_cost, currency, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (holding_id, profile["profile_id"], asset["asset_id"], quantity, average_cost, asset["currency"], note),
            )
        return {
            "holding_id": holding_id,
            "symbol": symbol,
            "quantity": quantity,
            "average_cost": average_cost,
            "note": note,
        }

    def update_user_portfolio_holding(
        self,
        auth_user_id: str,
        holding_id: str,
        quantity: float | None,
        average_cost: float | None,
        note: str | None,
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE portfolio_holdings
                SET quantity = COALESCE(?, quantity),
                    average_cost = COALESCE(?, average_cost),
                    note = COALESCE(?, note),
                    updated_at = CURRENT_TIMESTAMP
                WHERE holding_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                """,
                (quantity, average_cost, note, holding_id, auth_user_id),
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                """
                SELECT h.holding_id, a.symbol, h.quantity, h.average_cost, h.note
                FROM portfolio_holdings h
                JOIN assets a ON a.asset_id = h.asset_id
                WHERE h.holding_id = ?
                """,
                (holding_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "holding_id": row["holding_id"],
            "symbol": row["symbol"],
            "quantity": row["quantity"],
            "average_cost": row["average_cost"],
            "note": row["note"],
        }

    def delete_user_portfolio_holding(self, auth_user_id: str, holding_id: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM portfolio_holdings
                WHERE holding_id = ?
                  AND profile_id IN (SELECT profile_id FROM profiles WHERE auth_user_id = ?)
                """,
                (holding_id, auth_user_id),
            )
            return cur.rowcount > 0

    # -- transactions -----------------------------------------------------------

    def list_portfolio_transactions(
        self, auth_user_id: str, *, holding_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if holding_id is not None:
            sql = """
                SELECT t.transaction_id, t.holding_id, a.symbol, t.transaction_type,
                       t.quantity, t.price_per_unit, t.fee, t.currency,
                       t.transaction_date, t.note, t.created_at
                FROM portfolio_transactions t
                JOIN assets a ON a.asset_id = t.asset_id
                JOIN profiles p ON p.profile_id = t.profile_id
                WHERE p.auth_user_id = ? AND t.holding_id = ?
                ORDER BY t.transaction_date DESC, t.created_at DESC
                LIMIT ?
            """
            params: tuple[Any, ...] = (auth_user_id, holding_id, limit)
        else:
            sql = """
                SELECT t.transaction_id, t.holding_id, a.symbol, t.transaction_type,
                       t.quantity, t.price_per_unit, t.fee, t.currency,
                       t.transaction_date, t.note, t.created_at
                FROM portfolio_transactions t
                JOIN assets a ON a.asset_id = t.asset_id
                JOIN profiles p ON p.profile_id = t.profile_id
                WHERE p.auth_user_id = ?
                ORDER BY t.transaction_date DESC, t.created_at DESC
                LIMIT ?
            """
            params = (auth_user_id, limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                "transaction_id": row["transaction_id"],
                "holding_id": row["holding_id"],
                "symbol": row["symbol"],
                "transaction_type": row["transaction_type"],
                "quantity": row["quantity"],
                "price_per_unit": row["price_per_unit"],
                "fee": row["fee"],
                "currency": row["currency"],
                "transaction_date": row["transaction_date"],
                "note": row["note"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

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
    ) -> dict[str, Any]:
        transaction_id = str(uuid.uuid4())
        with self.connect() as conn:
            holding = conn.execute(
                """
                SELECT h.holding_id, h.profile_id, h.asset_id, h.quantity, h.average_cost,
                       a.currency, p.auth_user_id
                FROM portfolio_holdings h
                JOIN assets a ON a.asset_id = h.asset_id
                JOIN profiles p ON p.profile_id = h.profile_id
                WHERE h.holding_id = ?
                """,
                (holding_id,),
            ).fetchone()
            if holding is None or holding["auth_user_id"] != auth_user_id:
                raise LookupError("holding not found")

            conn.execute(
                """
                INSERT INTO portfolio_transactions
                  (transaction_id, holding_id, profile_id, asset_id, transaction_type,
                   quantity, price_per_unit, fee, currency, transaction_date, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    holding_id,
                    holding["profile_id"],
                    holding["asset_id"],
                    transaction_type,
                    quantity,
                    price_per_unit,
                    fee,
                    holding["currency"],
                    transaction_date,
                    note,
                ),
            )

            # Auto-recalculate holding quantity/average_cost
            old_qty = holding["quantity"] or 0.0
            old_avg = holding["average_cost"] or 0.0
            if transaction_type == "buy":
                new_qty = old_qty + quantity
                new_avg = (old_avg * old_qty + price_per_unit * quantity + fee) / new_qty if new_qty > 0 else 0.0
                conn.execute(
                    "UPDATE portfolio_holdings SET quantity = ?, average_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE holding_id = ?",
                    (new_qty, new_avg, holding_id),
                )
            elif transaction_type == "sell":
                new_qty = old_qty - quantity
                if new_qty <= 0:
                    conn.execute("DELETE FROM portfolio_holdings WHERE holding_id = ?", (holding_id,))
                else:
                    conn.execute(
                        "UPDATE portfolio_holdings SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE holding_id = ?",
                        (new_qty, holding_id),
                    )

        return {
            "transaction_id": transaction_id,
            "holding_id": holding_id,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "price_per_unit": price_per_unit,
            "fee": fee,
            "transaction_date": transaction_date,
            "note": note,
        }

    # -- returns & snapshots ----------------------------------------------------

    def fetch_portfolio_returns(self, auth_user_id: str, *, days: int = 365) -> dict[str, Any]:
        holdings = self.list_user_portfolio_holdings(auth_user_id)
        if not holdings:
            return {"summary": None, "holdings": [], "history": []}

        symbols = [h["symbol"] for h in holdings]
        placeholders = ",".join("?" for _ in symbols)
        with self.connect() as conn:
            price_rows = conn.execute(
                f"""
                SELECT a.symbol, dp.close
                FROM daily_prices dp
                JOIN assets a ON a.asset_id = dp.asset_id
                WHERE a.symbol IN ({placeholders})
                  AND dp.date = (
                    SELECT MAX(dp2.date) FROM daily_prices dp2 WHERE dp2.asset_id = dp.asset_id
                  )
                """,
                symbols,
            ).fetchall()
        latest_prices = {row["symbol"]: row["close"] for row in price_rows}

        snapshots = self.fetch_portfolio_snapshots(auth_user_id, days=days)
        previous_snapshot = snapshots[0] if snapshots else None

        summary, holding_returns = compute_portfolio_returns(
            holdings, latest_prices, previous_snapshot=previous_snapshot
        )
        return {
            "summary": summary.as_dict(),
            "holdings": [h.as_dict() for h in holding_returns],
            "history": snapshots,
        }

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
    ) -> None:
        snapshot_id = str(uuid.uuid4())
        with self.connect() as conn:
            profile = conn.execute("SELECT profile_id FROM profiles WHERE auth_user_id = ?", (auth_user_id,)).fetchone()
            if profile is None:
                raise LookupError("profile not found")
            conn.execute(
                """
                INSERT INTO portfolio_snapshots
                  (snapshot_id, profile_id, snapshot_date, total_cost, total_value,
                   total_return, total_return_pct, daily_return_pct, holdings_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (profile_id, snapshot_date) DO UPDATE SET
                  total_cost = excluded.total_cost,
                  total_value = excluded.total_value,
                  total_return = excluded.total_return,
                  total_return_pct = excluded.total_return_pct,
                  daily_return_pct = excluded.daily_return_pct,
                  holdings_json = excluded.holdings_json
                """,
                (
                    snapshot_id,
                    profile["profile_id"],
                    snapshot_date,
                    total_cost,
                    total_value,
                    total_return,
                    total_return_pct,
                    daily_return_pct,
                    holdings_json,
                ),
            )

    def fetch_portfolio_snapshots(self, auth_user_id: str, *, days: int = 365) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.snapshot_id, s.snapshot_date, s.total_cost, s.total_value,
                       s.total_return, s.total_return_pct, s.daily_return_pct,
                       s.holdings_json, s.created_at
                FROM portfolio_snapshots s
                JOIN profiles p ON p.profile_id = s.profile_id
                WHERE p.auth_user_id = ?
                  AND s.snapshot_date >= date('now', ?)
                ORDER BY s.snapshot_date DESC
                """,
                (auth_user_id, f"-{days} days"),
            ).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "snapshot_date": row["snapshot_date"],
                "total_cost": row["total_cost"],
                "total_value": row["total_value"],
                "total_return": row["total_return"],
                "total_return_pct": row["total_return_pct"],
                "daily_return_pct": row["daily_return_pct"],
                "holdings": json.loads(row["holdings_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
