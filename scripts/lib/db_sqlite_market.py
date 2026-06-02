from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


class SQLiteMarketMixin:
    def upsert_prices(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO daily_prices (
                  asset_id, date, open, high, low, close, adj_close, volume, source, provider, currency, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (asset_id, date) DO UPDATE SET
                  open = excluded.open,
                  high = excluded.high,
                  low = excluded.low,
                  close = excluded.close,
                  adj_close = excluded.adj_close,
                  volume = excluded.volume,
                  source = excluded.source,
                  provider = excluded.provider,
                  currency = excluded.currency,
                  fetched_at = excluded.fetched_at
                """,
                [
                    (
                        row["asset_id"],
                        self._to_db_date(row["date"]),
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("adj_close"),
                        row.get("volume"),
                        row.get("source"),
                        row.get("provider"),
                        row.get("currency"),
                        self._to_db_timestamp(row.get("fetched_at")),
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def upsert_indicators(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO daily_indicators (
                  asset_id, date, return_1d, return_1w, return_1m, return_3m, return_6m, return_ytd,
                  ma5, ma20, ma50, ma120, rsi14, vol20, drawdown_52w, high_52w
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (asset_id, date) DO UPDATE SET
                  return_1d = excluded.return_1d,
                  return_1w = excluded.return_1w,
                  return_1m = excluded.return_1m,
                  return_3m = excluded.return_3m,
                  return_6m = excluded.return_6m,
                  return_ytd = excluded.return_ytd,
                  ma5 = excluded.ma5,
                  ma20 = excluded.ma20,
                  ma50 = excluded.ma50,
                  ma120 = excluded.ma120,
                  rsi14 = excluded.rsi14,
                  vol20 = excluded.vol20,
                  drawdown_52w = excluded.drawdown_52w,
                  high_52w = excluded.high_52w,
                  updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        row["asset_id"],
                        self._to_db_date(row["date"]),
                        row.get("return_1d"),
                        row.get("return_1w"),
                        row.get("return_1m"),
                        row.get("return_3m"),
                        row.get("return_6m"),
                        row.get("return_ytd"),
                        row.get("ma5"),
                        row.get("ma20"),
                        row.get("ma50"),
                        row.get("ma120"),
                        row.get("rsi14"),
                        row.get("vol20"),
                        row.get("drawdown_52w"),
                        row.get("high_52w"),
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self.connect() as conn:
            row = conn.execute("SELECT holder, expires_at FROM job_locks WHERE lock_name = ?", (lock_name,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO job_locks (lock_name, holder, acquired_at, expires_at) VALUES (?, ?, ?, ?)",
                    (lock_name, holder, self._to_db_timestamp(now), self._to_db_timestamp(expires_at)),
                )
                return True
            existing_expires_at = self._coerce_datetime(row["expires_at"])
            if row["holder"] == holder or (existing_expires_at is not None and existing_expires_at <= now):
                conn.execute(
                    "UPDATE job_locks SET holder = ?, acquired_at = ?, expires_at = ? WHERE lock_name = ?",
                    (holder, self._to_db_timestamp(now), self._to_db_timestamp(expires_at), lock_name),
                )
                return True
        return False

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM job_locks WHERE lock_name = ? AND holder = ?", (lock_name, holder))

    def fetch_latest_price_dates(self, asset_ids: list[int]) -> dict[int, date]:
        if not asset_ids:
            return {}
        placeholders = ",".join(["?"] * len(asset_ids))
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT asset_id, max(date) AS latest_date FROM daily_prices WHERE asset_id IN ({placeholders}) GROUP BY asset_id",
                asset_ids,
            ).fetchall()
        result: dict[int, date] = {}
        for row in rows:
            latest = row["latest_date"]
            parsed = date.fromisoformat(latest) if isinstance(latest, str) else latest
            if parsed is not None:
                result[int(row["asset_id"])] = parsed
        return result
