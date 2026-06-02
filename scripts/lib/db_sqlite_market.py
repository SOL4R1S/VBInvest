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

    def fetch_watchlist_collection_status(self, slug: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                WITH wl_assets AS (
                  SELECT a.asset_id, a.symbol, a.display_name_ko, a.exchange, wm.sort_order
                  FROM watchlists w
                  JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
                  JOIN assets a ON a.asset_id = wm.asset_id
                  WHERE w.slug = ? AND w.archived_at IS NULL AND a.active = 1
                ),
                price_counts AS (
                  SELECT dp.asset_id,
                         COUNT(*) AS price_rows,
                         MAX(dp.date) AS latest_price_date,
                         SUM(CASE WHEN COALESCE(dp.provider, dp.source) = 'synthetic' THEN 1 ELSE 0 END) AS synthetic_rows
                  FROM daily_prices dp
                  JOIN wl_assets wa ON wa.asset_id = dp.asset_id
                  GROUP BY dp.asset_id
                ),
                latest_dates AS (
                  SELECT dp.asset_id, MAX(dp.date) AS latest_price_date
                  FROM daily_prices dp
                  JOIN wl_assets wa ON wa.asset_id = dp.asset_id
                  GROUP BY dp.asset_id
                ),
                latest_prices AS (
                  SELECT dp.asset_id,
                         COALESCE(dp.provider, dp.source) AS provider,
                         dp.fetched_at AS latest_fetched_at
                  FROM daily_prices dp
                  JOIN latest_dates ld ON ld.asset_id = dp.asset_id AND ld.latest_price_date = dp.date
                  WHERE dp.fetched_at = (
                    SELECT MAX(inner_price.fetched_at)
                    FROM daily_prices inner_price
                    WHERE inner_price.asset_id = dp.asset_id AND inner_price.date = dp.date
                  )
                ),
                indicator_counts AS (
                  SELECT di.asset_id, COUNT(*) AS indicator_rows
                  FROM daily_indicators di
                  JOIN wl_assets wa ON wa.asset_id = di.asset_id
                  GROUP BY di.asset_id
                )
                SELECT wa.symbol, wa.display_name_ko, wa.exchange, lp.provider,
                       pc.latest_price_date, lp.latest_fetched_at,
                       COALESCE(pc.price_rows, 0) AS price_rows,
                       COALESCE(ic.indicator_rows, 0) AS indicator_rows,
                       COALESCE(pc.synthetic_rows, 0) > 0 AS has_synthetic
                FROM wl_assets wa
                LEFT JOIN price_counts pc ON pc.asset_id = wa.asset_id
                LEFT JOIN latest_prices lp ON lp.asset_id = wa.asset_id
                LEFT JOIN indicator_counts ic ON ic.asset_id = wa.asset_id
                ORDER BY wa.sort_order, wa.symbol
                """,
                (slug,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            price_rows = int(row["price_rows"])
            has_synthetic = bool(row["has_synthetic"])
            latest_price_date = row["latest_price_date"]
            parsed_date = date.fromisoformat(latest_price_date) if isinstance(latest_price_date, str) else latest_price_date
            result.append(
                {
                    "symbol": row["symbol"],
                    "display_name_ko": row["display_name_ko"],
                    "exchange": row["exchange"],
                    "provider": row["provider"],
                    "latest_price_date": parsed_date,
                    "latest_fetched_at": self._coerce_datetime(row["latest_fetched_at"]),
                    "price_rows": price_rows,
                    "indicator_rows": int(row["indicator_rows"]),
                    "has_synthetic": has_synthetic,
                    "status": self._collection_status(price_rows, has_synthetic),
                }
            )
        return result

    def _collection_status(self, price_rows: int, has_synthetic: bool) -> str:
        if price_rows == 0:
            return "missing"
        if has_synthetic:
            return "synthetic"
        return "collected"
