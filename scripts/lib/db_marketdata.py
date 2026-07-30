"""VBinvestDB MarketDataMixin — extracted from db.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from scripts.lib.db_base import _collection_status


class MarketDataMixin:

    """Mixin — requires self.connect() from VBinvestDB."""


    def fetch_watchlist_assets(self, slug: str) -> list[dict[str, Any]]:
        query = """
        SELECT a.asset_id, a.symbol, a.display_name_ko, a.exchange, a.currency
        FROM watchlists w
        JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        JOIN assets a ON a.asset_id = wm.asset_id
        WHERE w.slug = %s AND a.active = TRUE
        ORDER BY wm.sort_order, a.symbol
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (slug,))
            return [
                {
                    "asset_id": row[0],
                    "symbol": row[1],
                    "display_name_ko": row[2],
                    "exchange": row[3],
                    "currency": row[4],
                }
                for row in cur.fetchall()
            ]


    def ensure_assets_for_refresh(self, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not assets:
            return []
        ensured: list[dict[str, Any]] = []
        with self.connect() as conn, conn.cursor() as cur:
            for asset in assets:
                symbol = str(asset.get("symbol", "")).strip().upper()
                if not symbol:
                    continue
                cur.execute(
                    """
                    INSERT INTO assets (symbol, display_name_ko, exchange, currency)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                      display_name_ko = COALESCE(assets.display_name_ko, EXCLUDED.display_name_ko),
                      exchange = COALESCE(assets.exchange, EXCLUDED.exchange),
                      currency = COALESCE(assets.currency, EXCLUDED.currency),
                      updated_at = now()
                    RETURNING asset_id, symbol, display_name_ko, exchange, currency
                    """,
                    (symbol, asset.get("display_name_ko"), asset.get("exchange"), asset.get("currency")),
                )
                row = cur.fetchone()
                ensured.append(
                    {
                        **asset,
                        "asset_id": row[0],
                        "symbol": row[1],
                        "display_name_ko": row[2] or asset.get("display_name_ko"),
                        "exchange": row[3] or asset.get("exchange"),
                        "currency": row[4] or asset.get("currency"),
                    }
                )
        return ensured


    def upsert_prices(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        sql = """
        INSERT INTO daily_prices (
          asset_id, date, open, high, low, close, adj_close, volume, source, provider, currency, fetched_at
        ) VALUES (
          %(asset_id)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(adj_close)s, %(volume)s,
          %(source)s, %(provider)s, %(currency)s, %(fetched_at)s
        )
        ON CONFLICT (asset_id, date) DO UPDATE SET
          open = EXCLUDED.open,
          high = EXCLUDED.high,
          low = EXCLUDED.low,
          close = EXCLUDED.close,
          adj_close = EXCLUDED.adj_close,
          volume = EXCLUDED.volume,
          source = EXCLUDED.source,
          provider = EXCLUDED.provider,
          currency = EXCLUDED.currency,
          fetched_at = EXCLUDED.fetched_at
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)
            return len(rows)


    def upsert_indicators(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        sql = """
        INSERT INTO daily_indicators (
          asset_id, date, return_1d, return_1w, return_1m, return_3m, return_6m, return_ytd,
          ma5, ma20, ma50, ma120, rsi14, vol20, drawdown_52w, high_52w
        ) VALUES (
          %(asset_id)s, %(date)s, %(return_1d)s, %(return_1w)s, %(return_1m)s, %(return_3m)s, %(return_6m)s, %(return_ytd)s,
          %(ma5)s, %(ma20)s, %(ma50)s, %(ma120)s, %(rsi14)s, %(vol20)s, %(drawdown_52w)s, %(high_52w)s
        )
        ON CONFLICT (asset_id, date) DO UPDATE SET
          return_1d = EXCLUDED.return_1d,
          return_1w = EXCLUDED.return_1w,
          return_1m = EXCLUDED.return_1m,
          return_3m = EXCLUDED.return_3m,
          return_6m = EXCLUDED.return_6m,
          return_ytd = EXCLUDED.return_ytd,
          ma5 = EXCLUDED.ma5,
          ma20 = EXCLUDED.ma20,
          ma50 = EXCLUDED.ma50,
          ma120 = EXCLUDED.ma120,
          rsi14 = EXCLUDED.rsi14,
          vol20 = EXCLUDED.vol20,
          drawdown_52w = EXCLUDED.drawdown_52w,
          high_52w = EXCLUDED.high_52w,
          updated_at = now()
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)
            return len(rows)


    def fetch_latest_price_dates(self, asset_ids: list[int]) -> dict[int, datetime.date]:
        if not asset_ids:
            return {}
        placeholders = ",".join(["%s"] * len(asset_ids))
        sql = (
            "SELECT asset_id, max(date) AS latest_date "
            f"FROM daily_prices WHERE asset_id IN ({placeholders}) GROUP BY asset_id"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, asset_ids)
            rows = cur.fetchall()
        return {int(asset_id): latest_date for asset_id, latest_date in rows if latest_date is not None}


    def fetch_price_date_ranges(self, asset_ids: list[int]) -> dict[int, dict[str, datetime.date]]:
        if not asset_ids:
            return {}
        placeholders = ",".join(["%s"] * len(asset_ids))
        sql = (
            "SELECT asset_id, min(date) AS earliest_date, max(date) AS latest_date "
            f"FROM daily_prices WHERE asset_id IN ({placeholders}) GROUP BY asset_id"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, asset_ids)
            rows = cur.fetchall()
        return {
            int(asset_id): {"earliest_date": earliest_date, "latest_date": latest_date}
            for asset_id, earliest_date, latest_date in rows
            if earliest_date is not None and latest_date is not None
        }


    def fetch_watchlist_collection_status(self, slug: str) -> list[dict[str, Any]]:
        query = """
        WITH wl_assets AS (
          SELECT a.asset_id, a.symbol, a.display_name_ko, a.exchange, wm.sort_order
          FROM watchlists w
          JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
          JOIN assets a ON a.asset_id = wm.asset_id
          WHERE w.slug = %s AND a.active = TRUE
        ),
        price_counts AS (
          SELECT dp.asset_id,
                 COUNT(*) AS price_rows,
                 MAX(dp.date) AS latest_price_date,
                 BOOL_OR(COALESCE(dp.provider, dp.source) = 'synthetic') AS has_synthetic
          FROM daily_prices dp
          JOIN wl_assets wa ON wa.asset_id = dp.asset_id
          GROUP BY dp.asset_id
        ),
        latest_prices AS (
          SELECT DISTINCT ON (dp.asset_id)
                 dp.asset_id,
                 COALESCE(dp.provider, dp.source) AS provider,
                 dp.fetched_at AS latest_fetched_at
          FROM daily_prices dp
          JOIN wl_assets wa ON wa.asset_id = dp.asset_id
          ORDER BY dp.asset_id, dp.date DESC, dp.fetched_at DESC
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
               COALESCE(pc.has_synthetic, FALSE) AS has_synthetic
        FROM wl_assets wa
        LEFT JOIN price_counts pc ON pc.asset_id = wa.asset_id
        LEFT JOIN latest_prices lp ON lp.asset_id = wa.asset_id
        LEFT JOIN indicator_counts ic ON ic.asset_id = wa.asset_id
        ORDER BY wa.sort_order, wa.symbol
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (slug,))
            rows = cur.fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            price_rows = int(row[6])
            has_synthetic = bool(row[8])
            result.append(
                {
                    "symbol": row[0],
                    "display_name_ko": row[1],
                    "exchange": row[2],
                    "provider": row[3],
                    "latest_price_date": row[4],
                    "latest_fetched_at": row[5],
                    "price_rows": price_rows,
                    "indicator_rows": int(row[7]),
                    "has_synthetic": has_synthetic,
                    "status": _collection_status(price_rows, has_synthetic),
                }
            )
        return result


    def fetch_dashboard_items(self, slug: str, *, days: int = 1260) -> list[dict[str, Any]]:
        assets = self.fetch_watchlist_assets(slug)
        if not assets:
            return []
        views = self.fetch_latest_research_views(slug)
        items: list[dict[str, Any]] = []
        query = """
        SELECT p.date, p.open, p.high, p.low, p.close, p.volume, p.source,
               i.return_1d, i.return_1w, i.return_1m, i.return_3m, i.return_6m, i.return_ytd,
               i.ma5, i.ma20, i.ma50, i.ma120, i.rsi14, i.vol20, i.drawdown_52w, i.high_52w
        FROM daily_prices p
        LEFT JOIN daily_indicators i ON i.asset_id = p.asset_id AND i.date = p.date
        WHERE p.asset_id = %s
        ORDER BY p.date DESC
        LIMIT %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            for asset in assets:
                cur.execute(query, (asset["asset_id"], days))
                rows = cur.fetchall()
                if not rows:
                    continue
                numeric_columns = [
                    "open", "high", "low", "close", "volume",
                    "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_ytd",
                    "ma5", "ma20", "ma50", "ma120", "rsi14", "vol20", "drawdown_52w", "high_52w",
                ]
                frame = pd.DataFrame(
                    rows,
                    columns=[
                        "date", "open", "high", "low", "close", "volume", "source",
                        "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_ytd",
                        "ma5", "ma20", "ma50", "ma120", "rsi14", "vol20", "drawdown_52w", "high_52w",
                    ],
                ).sort_values("date").reset_index(drop=True)
                for column in numeric_columns:
                    frame[column] = pd.to_numeric(frame[column], errors="coerce")
                item = {"asset": asset, "history": frame}
                item.update(views.get(asset["symbol"], {}))
                items.append(item)
        return items


    def fetch_asset_dashboard_item(self, symbol: str, *, days: int = 1260) -> dict[str, Any] | None:
        query = """
        SELECT asset_id, symbol, display_name_ko, exchange, currency
        FROM assets
        WHERE symbol = %s AND active = TRUE
        LIMIT 1
        """
        history_query = """
        SELECT p.date, p.open, p.high, p.low, p.close, p.volume, p.source,
               i.return_1d, i.return_1w, i.return_1m, i.return_3m, i.return_6m, i.return_ytd,
               i.ma5, i.ma20, i.ma50, i.ma120, i.rsi14, i.vol20, i.drawdown_52w, i.high_52w
        FROM daily_prices p
        LEFT JOIN daily_indicators i ON i.asset_id = p.asset_id AND i.date = p.date
        WHERE p.asset_id = %s
        ORDER BY p.date DESC
        LIMIT %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (symbol,))
            asset_row = cur.fetchone()
            if asset_row is None:
                return None
            asset = {
                "asset_id": asset_row[0],
                "symbol": asset_row[1],
                "display_name_ko": asset_row[2],
                "exchange": asset_row[3],
                "currency": asset_row[4],
            }
            cur.execute(history_query, (asset["asset_id"], days))
            rows = cur.fetchall()
            if not rows:
                return None
            news = self.fetch_recent_news_for_asset(asset["asset_id"])
            disclosures = self.fetch_recent_disclosures_for_asset(asset["asset_id"])
        frame = pd.DataFrame(
            rows,
            columns=[
                "date", "open", "high", "low", "close", "volume", "source",
                "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_ytd",
                "ma5", "ma20", "ma50", "ma120", "rsi14", "vol20", "drawdown_52w", "high_52w",
            ],
        ).sort_values("date").reset_index(drop=True)
        for column in [
            "open", "high", "low", "close", "volume",
            "return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_ytd",
            "ma5", "ma20", "ma50", "ma120", "rsi14", "vol20", "drawdown_52w", "high_52w",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return {"asset": asset, "history": frame, "news": news, "disclosures": disclosures}
