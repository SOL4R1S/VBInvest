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
    return {"holding_id": holding_id, "symbol": symbol, "quantity": quantity, "average_cost": average_cost, "note": note}


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
