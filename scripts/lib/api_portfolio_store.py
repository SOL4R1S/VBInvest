from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from scripts.lib.db import VBinvestDB


def list_user_portfolio_holdings(db: VBinvestDB, auth_user_id: str) -> list[dict[str, Any]]:
    query = """
    SELECT h.holding_id::text, a.symbol, h.quantity, h.average_cost, h.note
    FROM portfolio_holdings h
    JOIN profiles p ON p.profile_id = h.profile_id
    JOIN assets a ON a.asset_id = h.asset_id
    WHERE p.auth_user_id::text = %s
    ORDER BY a.symbol
    """
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, (auth_user_id,))
        return [_holding_row(row) for row in cur.fetchall()]


def create_user_portfolio_holding(
    db: VBinvestDB,
    auth_user_id: str,
    symbol: str,
    quantity: float,
    average_cost: float | None,
    note: str | None,
) -> dict[str, Any]:
    holding_id = str(uuid.uuid4())
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
        profile = cur.fetchone()
        cur.execute("SELECT asset_id FROM assets WHERE symbol = %s AND active = TRUE", (symbol,))
        asset = cur.fetchone()
        if profile is None or asset is None:
            raise LookupError("profile or asset not found")
        cur.execute(
            """
            INSERT INTO portfolio_holdings (holding_id, profile_id, asset_id, quantity, average_cost, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING holding_id::text
            """,
            (holding_id, profile[0], asset[0], quantity, average_cost, note),
        )
    return {
        "holding_id": holding_id,
        "symbol": symbol,
        "quantity": quantity,
        "average_cost": average_cost,
        "note": note,
    }


def update_user_portfolio_holding(
    db: VBinvestDB,
    auth_user_id: str,
    holding_id: str,
    quantity: float | None,
    average_cost: float | None,
    note: str | None,
) -> dict[str, Any] | None:
    query = """
    UPDATE portfolio_holdings h
    SET quantity = COALESCE(%s, h.quantity),
        average_cost = COALESCE(%s, h.average_cost),
        note = COALESCE(%s, h.note),
        updated_at = now()
    FROM profiles p
    WHERE p.profile_id = h.profile_id AND p.auth_user_id::text = %s AND h.holding_id::text = %s
    RETURNING h.holding_id::text
    """
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, (quantity, average_cost, note, auth_user_id, holding_id))
        if cur.fetchone() is None:
            return None
    return get_holding(db, auth_user_id, holding_id)


def delete_user_portfolio_holding(db: VBinvestDB, auth_user_id: str, holding_id: str) -> bool:
    query = """
    DELETE FROM portfolio_holdings h
    USING profiles p
    WHERE p.profile_id = h.profile_id AND p.auth_user_id::text = %s AND h.holding_id::text = %s
    """
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, (auth_user_id, holding_id))
        return cur.rowcount > 0


def get_holding(db: VBinvestDB, auth_user_id: str, holding_id: str) -> dict[str, Any] | None:
    query = """
    SELECT h.holding_id::text, a.symbol, h.quantity, h.average_cost, h.note
    FROM portfolio_holdings h
    JOIN profiles p ON p.profile_id = h.profile_id
    JOIN assets a ON a.asset_id = h.asset_id
    WHERE p.auth_user_id::text = %s AND h.holding_id::text = %s
    """
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, (auth_user_id, holding_id))
        row = cur.fetchone()
    return None if row is None else _holding_row(row)


def _holding_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "holding_id": row[0],
        "symbol": row[1],
        "quantity": _json_number(row[2]),
        "average_cost": _json_number(row[3]),
        "note": row[4],
    }


def _json_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


# -- transactions ---------------------------------------------------------------


def list_portfolio_transactions(
    db: VBinvestDB, auth_user_id: str, *, holding_id: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    if holding_id is not None:
        query = """
            SELECT t.transaction_id::text, t.holding_id::text, a.symbol, t.transaction_type,
                   t.quantity, t.price_per_unit, t.fee, t.currency,
                   t.transaction_date, t.note, t.created_at
            FROM portfolio_transactions t
            JOIN assets a ON a.asset_id = t.asset_id
            JOIN profiles p ON p.profile_id = t.profile_id
            WHERE p.auth_user_id::text = %s AND t.holding_id::text = %s
            ORDER BY t.transaction_date DESC, t.created_at DESC
            LIMIT %s
        """
        params: tuple[Any, ...] = (auth_user_id, holding_id, limit)
    else:
        query = """
            SELECT t.transaction_id::text, t.holding_id::text, a.symbol, t.transaction_type,
                   t.quantity, t.price_per_unit, t.fee, t.currency,
                   t.transaction_date, t.note, t.created_at
            FROM portfolio_transactions t
            JOIN assets a ON a.asset_id = t.asset_id
            JOIN profiles p ON p.profile_id = t.profile_id
            WHERE p.auth_user_id::text = %s
            ORDER BY t.transaction_date DESC, t.created_at DESC
            LIMIT %s
        """
        params = (auth_user_id, limit)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return [_transaction_row(row) for row in cur.fetchall()]


def create_portfolio_transaction(
    db: VBinvestDB,
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
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT h.holding_id::text, h.profile_id, h.asset_id, h.quantity, h.average_cost,
                   a.currency, p.auth_user_id::text
            FROM portfolio_holdings h
            JOIN assets a ON a.asset_id = h.asset_id
            JOIN profiles p ON p.profile_id = h.profile_id
            WHERE h.holding_id::text = %s
            """,
            (holding_id,),
        )
        holding = cur.fetchone()
        if holding is None or holding[6] != auth_user_id:
            raise LookupError("holding not found")

        cur.execute(
            """
            INSERT INTO portfolio_transactions
              (transaction_id, holding_id, profile_id, asset_id, transaction_type,
               quantity, price_per_unit, fee, currency, transaction_date, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                transaction_id, holding[0], holding[1], holding[2],
                transaction_type, quantity, price_per_unit, fee,
                holding[5], transaction_date, note,
            ),
        )

        old_qty = float(holding[3] or 0)
        old_avg = float(holding[4] or 0)
        if transaction_type == "buy":
            new_qty = old_qty + quantity
            new_avg = (old_avg * old_qty + price_per_unit * quantity + fee) / new_qty if new_qty > 0 else 0.0
            cur.execute(
                "UPDATE portfolio_holdings SET quantity = %s, average_cost = %s, updated_at = now() WHERE holding_id = %s",
                (new_qty, new_avg, holding[0]),
            )
        elif transaction_type == "sell":
            new_qty = old_qty - quantity
            if new_qty <= 0:
                cur.execute("DELETE FROM portfolio_holdings WHERE holding_id = %s", (holding[0],))
            else:
                cur.execute(
                    "UPDATE portfolio_holdings SET quantity = %s, updated_at = now() WHERE holding_id = %s",
                    (new_qty, holding[0]),
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


def _transaction_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "transaction_id": row[0],
        "holding_id": row[1],
        "symbol": row[2],
        "transaction_type": row[3],
        "quantity": _json_number(row[4]),
        "price_per_unit": _json_number(row[5]),
        "fee": _json_number(row[6]),
        "currency": row[7],
        "transaction_date": str(row[8]) if row[8] is not None else None,
        "note": row[9],
        "created_at": str(row[10]) if row[10] is not None else None,
    }


# -- returns & snapshots --------------------------------------------------------


def fetch_portfolio_returns(db: VBinvestDB, auth_user_id: str, *, days: int = 365) -> dict[str, Any]:
    from scripts.lib.portfolio_returns import compute_portfolio_returns

    holdings = list_user_portfolio_holdings(db, auth_user_id)
    if not holdings:
        return {"summary": None, "holdings": [], "history": []}

    symbols = [h["symbol"] for h in holdings]
    placeholders = ",".join("%s" for _ in symbols)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
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
        )
        latest_prices = {row[0]: float(row[1]) for row in cur.fetchall() if row[1] is not None}

    snapshots = fetch_portfolio_snapshots(db, auth_user_id, days=days)
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
    db: VBinvestDB,
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
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id::text = %s", (auth_user_id,))
        profile = cur.fetchone()
        if profile is None:
            raise LookupError("profile not found")
        cur.execute(
            """
            INSERT INTO portfolio_snapshots
              (snapshot_id, profile_id, snapshot_date, total_cost, total_value,
               total_return, total_return_pct, daily_return_pct, holdings_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, snapshot_date) DO UPDATE SET
              total_cost = EXCLUDED.total_cost,
              total_value = EXCLUDED.total_value,
              total_return = EXCLUDED.total_return,
              total_return_pct = EXCLUDED.total_return_pct,
              daily_return_pct = EXCLUDED.daily_return_pct,
              holdings_json = EXCLUDED.holdings_json
            """,
            (
                snapshot_id, profile[0], snapshot_date,
                total_cost, total_value, total_return, total_return_pct,
                daily_return_pct, holdings_json,
            ),
        )


def fetch_portfolio_snapshots(db: VBinvestDB, auth_user_id: str, *, days: int = 365) -> list[dict[str, Any]]:
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.snapshot_id::text, s.snapshot_date, s.total_cost, s.total_value,
                   s.total_return, s.total_return_pct, s.daily_return_pct,
                   s.holdings_json, s.created_at
            FROM portfolio_snapshots s
            JOIN profiles p ON p.profile_id = s.profile_id
            WHERE p.auth_user_id::text = %s
              AND s.snapshot_date >= CURRENT_DATE - %s
            ORDER BY s.snapshot_date DESC
            """,
            (auth_user_id, days),
        )
        return [_snapshot_row(row) for row in cur.fetchall()]


def _snapshot_row(row: tuple[Any, ...]) -> dict[str, Any]:
    import json

    holdings_raw = row[7]
    if isinstance(holdings_raw, str):
        holdings = json.loads(holdings_raw)
    elif isinstance(holdings_raw, dict | list):
        holdings = holdings_raw
    else:
        holdings = []
    return {
        "snapshot_id": row[0],
        "snapshot_date": str(row[1]) if row[1] is not None else None,
        "total_cost": _json_number(row[2]),
        "total_value": _json_number(row[3]),
        "total_return": _json_number(row[4]),
        "total_return_pct": _json_number(row[5]),
        "daily_return_pct": _json_number(row[6]),
        "holdings": holdings,
        "created_at": str(row[8]) if row[8] is not None else None,
    }
