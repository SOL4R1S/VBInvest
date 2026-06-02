from __future__ import annotations

import json
import os
import re
import uuid
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote_plus

import pandas as pd

from scripts.lib.ai_provider import build_research_ai_client_from_env
from scripts.lib.keychain import SecretStore, resolve_secret
from scripts.lib.research import build_on_demand_research_view, build_source_packet


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = "host.docker.internal"
    port: int = 5432
    database: str = "vbinvest"
    user: str = "vbinvest"
    password: str = ""

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        system_name: str | None = None,
        secret_store: SecretStore | None = None,
    ) -> "DatabaseConfig":
        return cls(
            host=env.get("VBINVEST_DB_HOST") or env.get("POSTGRES_HOST") or "host.docker.internal",
            port=int(env.get("VBINVEST_DB_PORT") or env.get("POSTGRES_PORT") or 5432),
            database=env.get("VBINVEST_DB_NAME") or env.get("POSTGRES_DB") or "vbinvest",
            user=env.get("VBINVEST_DB_USER") or env.get("POSTGRES_USER") or "vbinvest",
            password=resolve_secret(
                env,
                "POSTGRES_PASSWORD",
                aliases=("VBINVEST_DB_PASSWORD",),
                system_name=system_name,
                store=secret_store,
            ),
        )

    def dsn(self, *, mask_password: bool = True) -> str:
        user = quote_plus(self.user)
        password = "***" if mask_password and self.password else quote_plus(self.password)
        auth = user if not self.password else f"{user}:{password}"
        return f"postgresql://{auth}@{self.host}:{self.port}/{quote_plus(self.database)}"

    def safe_summary(self) -> str:
        password_state = "***" if self.password else "<unset>"
        return (
            f"host={self.host} port={self.port} database={self.database} "
            f"user={self.user} password={password_state}"
        )


def none_if_na(value: Any) -> Any:
    return None if pd.isna(value) else value


def json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _research_source_type(kind: str | None) -> str:
    if kind == "news":
        return "news"
    if kind == "disclosure":
        return "disclosure"
    if kind == "db_price_indicator":
        return "indicator"
    return "manual"


def _collection_status(price_rows: int, has_synthetic: bool) -> str:
    if price_rows == 0:
        return "missing"
    if has_synthetic:
        return "synthetic"
    return "collected"


def _profile_slug(auth_user_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", auth_user_id).strip("-").lower()
    return value or f"profile-{uuid.uuid4()}"


def build_price_rows(asset_id: int, frame: pd.DataFrame, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    fetched = fetched_at or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        provider = record.get("provider") or record.get("source")
        rows.append(
            {
                "asset_id": asset_id,
                "date": record["date"],
                "open": none_if_na(record.get("open")),
                "high": none_if_na(record.get("high")),
                "low": none_if_na(record.get("low")),
                "close": none_if_na(record.get("close")),
                "adj_close": none_if_na(record.get("adj_close")),
                "volume": none_if_na(record.get("volume")),
                "source": provider,
                "provider": provider,
                "currency": none_if_na(record.get("currency")),
                "fetched_at": fetched,
            }
        )
    return rows


def build_indicator_rows(asset_id: int, frame: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "return_1d",
        "return_1w",
        "return_1m",
        "return_3m",
        "return_6m",
        "return_ytd",
        "ma5",
        "ma20",
        "ma50",
        "ma120",
        "rsi14",
        "vol20",
        "drawdown_52w",
        "high_52w",
    ]
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        row = {"asset_id": asset_id, "date": record["date"]}
        for column in columns:
            row[column] = none_if_na(record.get(column))
        rows.append(row)
    return rows


class VBinvestDB:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for live DB access") from exc
        self._psycopg = psycopg

    @classmethod
    def from_local_config(
        cls,
        *,
        config_path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        from scripts.lib.db_factory import build_database_from_local_config

        return build_database_from_local_config(config_path=config_path, environ=environ)

    def connect(self):
        return self._psycopg.connect(self.config.dsn(mask_password=False))

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

    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None:
        query = """
        SELECT profile_id, auth_user_id, slug, name, email, auth_provider
        FROM profiles
        WHERE auth_user_id = %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "profile_id": row[0],
                "auth_user_id": str(row[1]),
                "slug": row[2],
                "name": row[3],
                "email": row[4],
                "auth_provider": row[5],
            }

    def ensure_profile_for_auth_user(self, auth_user_id: str, email: str | None) -> dict[str, Any]:
        slug = _profile_slug(auth_user_id)
        name = email.split("@", 1)[0] if email else slug
        query = """
        INSERT INTO profiles (slug, name, auth_user_id, email, auth_provider)
        VALUES (%s, %s, %s, %s, 'local')
        ON CONFLICT (auth_user_id) WHERE auth_user_id IS NOT NULL DO UPDATE SET
          email = COALESCE(profiles.email, EXCLUDED.email),
          updated_at = now()
        RETURNING profile_id, auth_user_id, slug, name, email, auth_provider
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (slug, name, auth_user_id, email))
            row = cur.fetchone()
            return {
                "profile_id": row[0],
                "auth_user_id": str(row[1]),
                "slug": row[2],
                "name": row[3],
                "email": row[4],
                "auth_provider": row[5],
            }

    def list_user_watchlists(self, auth_user_id: str) -> list[dict[str, Any]]:
        query = """
        SELECT w.watchlist_id, w.name_ko, w.slug, COALESCE(json_agg(a.symbol ORDER BY wm.sort_order) FILTER (WHERE a.symbol IS NOT NULL), '[]'::json)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id = %s AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko, w.slug
        ORDER BY w.sort_order, w.watchlist_id
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            return [
                {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": row[3] or []}
                for row in cur.fetchall()
            ]

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]) -> dict[str, Any]:
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
            slug = self._watchlist_slug(auth_user_id, name)
            cur.execute(
                """
                INSERT INTO watchlists (slug, name_ko, parent_type, sort_order, owner_profile_id, visibility)
                VALUES (%s, %s, 'global', 0, %s, 'private')
                ON CONFLICT (slug) DO UPDATE SET
                  name_ko = EXCLUDED.name_ko,
                  owner_profile_id = EXCLUDED.owner_profile_id,
                  archived_at = NULL,
                  updated_at = now()
                RETURNING watchlist_id, name_ko, slug
                """,
                (slug, name, profile_id),
            )
            row = cur.fetchone()
            watchlist_id = row[0]
            cur.execute("DELETE FROM watchlist_members WHERE watchlist_id = %s", (watchlist_id,))
            clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
            for index, symbol in enumerate(clean_symbols, start=1):
                asset_id = self._ensure_asset(cur, symbol)
                cur.execute(
                    """
                    INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (watchlist_id, asset_id) DO UPDATE SET sort_order = EXCLUDED.sort_order
                    """,
                    (watchlist_id, asset_id, index),
                )
            return {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": clean_symbols}

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str) -> dict[str, Any] | None:
        query = """
        SELECT w.watchlist_id, w.name_ko, w.slug, COALESCE(json_agg(a.symbol ORDER BY wm.sort_order) FILTER (WHERE a.symbol IS NOT NULL), '[]'::json)
        FROM watchlists w
        JOIN profiles p ON p.profile_id = w.owner_profile_id
        LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
        LEFT JOIN assets a ON a.asset_id = wm.asset_id
        WHERE p.auth_user_id = %s AND w.watchlist_id::text = %s AND w.archived_at IS NULL
        GROUP BY w.watchlist_id, w.name_ko, w.slug
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id, watchlist_id))
            row = cur.fetchone()
            if row is None:
                return None
            return {"watchlist_id": str(row[0]), "name": row[1], "slug": row[2], "symbols": row[3] or []}

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

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        sql = """
        INSERT INTO job_locks (lock_name, holder, expires_at)
        VALUES (%(lock_name)s, %(holder)s, now() + (%(ttl_seconds)s * interval '1 second'))
        ON CONFLICT (lock_name) DO UPDATE SET
          holder = EXCLUDED.holder,
          acquired_at = now(),
          expires_at = EXCLUDED.expires_at
        WHERE job_locks.expires_at <= now() OR job_locks.holder = EXCLUDED.holder
        RETURNING lock_name
        """
        params = {"lock_name": lock_name, "holder": holder, "ttl_seconds": ttl_seconds}
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        sql = "DELETE FROM job_locks WHERE lock_name = %s AND holder = %s"
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (lock_name, holder))

    def upsert_news_items(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        count = 0
        with self.connect() as conn, conn.cursor() as cur:
            for row in rows:
                params = dict(row)
                params["raw_json"] = json_dumps(params.get("raw_json"))
                sql = self._news_upsert_sql(params)
                cur.execute(sql, params)
                news_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO asset_news_map (asset_id, news_id, relevance)
                    VALUES (%(asset_id)s, %(news_id)s, %(relevance)s)
                    ON CONFLICT (asset_id, news_id) DO UPDATE SET relevance = EXCLUDED.relevance
                    """,
                    {
                        "asset_id": params["asset_id"],
                        "news_id": news_id,
                        "relevance": params.get("relevance"),
                    },
                )
                count += 1
        return count

    def upsert_disclosures(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        sql = """
        INSERT INTO disclosures (
          asset_id, market, provider, provider_disclosure_id, title, published_at, url, raw_json
        ) VALUES (
          %(asset_id)s, %(market)s, %(provider)s, %(provider_disclosure_id)s,
          %(title)s, %(published_at)s, %(url)s, %(raw_json)s::jsonb
        )
        ON CONFLICT (provider, provider_disclosure_id) WHERE provider_disclosure_id IS NOT NULL DO UPDATE SET
          asset_id = EXCLUDED.asset_id,
          market = EXCLUDED.market,
          title = EXCLUDED.title,
          published_at = EXCLUDED.published_at,
          url = EXCLUDED.url,
          raw_json = EXCLUDED.raw_json,
          updated_at = now()
        """
        prepared = []
        for row in rows:
            params = dict(row)
            params["raw_json"] = json_dumps(params.get("raw_json"))
            prepared.append(params)
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, prepared)
            return len(prepared)

    def _news_upsert_sql(self, row: dict[str, Any]) -> str:
        conflict = "(provider, content_hash) WHERE content_hash IS NOT NULL"
        if row.get("source_id"):
            conflict = "(provider, source_id) WHERE source_id IS NOT NULL"
        elif row.get("canonical_url"):
            conflict = "(canonical_url) WHERE canonical_url IS NOT NULL"
        return f"""
        INSERT INTO news_items (
          provider, source, source_id, url, canonical_url, title, published_at,
          content_hash, language, summary, raw_json
        ) VALUES (
          %(provider)s, %(source)s, %(source_id)s, %(url)s, %(canonical_url)s, %(title)s, %(published_at)s,
          %(content_hash)s, %(language)s, %(summary)s, %(raw_json)s::jsonb
        )
        ON CONFLICT {conflict} DO UPDATE SET
          source = EXCLUDED.source,
          url = EXCLUDED.url,
          canonical_url = EXCLUDED.canonical_url,
          title = EXCLUDED.title,
          published_at = EXCLUDED.published_at,
          content_hash = EXCLUDED.content_hash,
          language = EXCLUDED.language,
          summary = EXCLUDED.summary,
          raw_json = EXCLUDED.raw_json,
          updated_at = now()
        RETURNING news_id
        """

    def record_report_run(
        self,
        *,
        run_type: str,
        status: str,
        scope_type: str = "watchlist",
        scope_slug: str | None = None,
        failed_assets: list[str] | None = None,
        output_summary: str | None = None,
        output_path: str | None = None,
        error_message: str | None = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        sql = """
        INSERT INTO report_runs (
          run_id, run_type, scope_type, scope_slug, completed_at, status,
          failed_assets, output_summary, output_path, error_message
        ) VALUES (
          %(run_id)s, %(run_type)s, %(scope_type)s, %(scope_slug)s, now(), %(status)s,
          %(failed_assets)s::jsonb, %(output_summary)s, %(output_path)s, %(error_message)s
        )
        """
        params = {
            "run_id": run_id,
            "run_type": run_type,
            "scope_type": scope_type,
            "scope_slug": scope_slug,
            "status": status,
            "failed_assets": json.dumps(failed_assets or [], ensure_ascii=False),
            "output_summary": output_summary,
            "output_path": output_path,
            "error_message": error_message,
        }
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
        return run_id

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        sql = """
        SELECT run_id, run_type, scope_type, scope_slug, completed_at, status, failed_assets, output_summary, output_path, error_message
        FROM report_runs
        WHERE run_type = %s AND scope_slug IS NOT DISTINCT FROM %s
        ORDER BY completed_at DESC, run_id DESC
        LIMIT 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (run_type, scope_slug))
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "run_type": row[1],
            "scope_type": row[2],
            "scope_slug": row[3],
            "completed_at": row[4],
            "status": row[5],
            "failed_assets": row[6] or [],
            "output_summary": row[7],
            "output_path": row[8],
            "error_message": row[9],
        }

    def fetch_latest_successful_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        sql = """
        SELECT run_id, run_type, scope_type, scope_slug, completed_at, status, failed_assets, output_summary, output_path, error_message
        FROM report_runs
        WHERE run_type = %s AND scope_slug IS NOT DISTINCT FROM %s AND status = 'ok'
        ORDER BY completed_at DESC, run_id DESC
        LIMIT 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (run_type, scope_slug))
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "run_type": row[1],
            "scope_type": row[2],
            "scope_slug": row[3],
            "completed_at": row[4],
            "status": row[5],
            "failed_assets": row[6] or [],
            "output_summary": row[7],
            "output_path": row[8],
            "error_message": row[9],
        }

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

    def fetch_dashboard_items(self, slug: str, *, days: int = 260) -> list[dict[str, Any]]:
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

    def upsert_research_views(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        sql = """
        INSERT INTO research_views (
          target_type, target_slug, report_date, horizon, opinion, thesis,
          rationale, bull, base, bear, risks, triggers, sources,
          confidence, source_freshness_status, access_tier
        ) VALUES (
          %(target_type)s, %(target_slug)s, %(report_date)s, %(horizon)s, %(opinion)s, %(thesis)s,
          %(rationale)s::jsonb, %(bull)s, %(base)s, %(bear)s, %(risks)s::jsonb, %(triggers)s::jsonb, %(sources)s::jsonb,
          %(confidence)s, %(source_freshness_status)s, %(access_tier)s
        )
        ON CONFLICT (target_type, target_slug, report_date, horizon) DO UPDATE SET
          opinion = EXCLUDED.opinion,
          thesis = EXCLUDED.thesis,
          rationale = EXCLUDED.rationale,
          bull = EXCLUDED.bull,
          base = EXCLUDED.base,
          bear = EXCLUDED.bear,
          risks = EXCLUDED.risks,
          triggers = EXCLUDED.triggers,
          sources = EXCLUDED.sources,
          confidence = EXCLUDED.confidence,
          source_freshness_status = EXCLUDED.source_freshness_status,
          access_tier = EXCLUDED.access_tier,
          updated_at = now()
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, rows)
            return len(rows)

    def record_research_sources(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        sql = """
        INSERT INTO research_sources (
          source_type, provider, title, url, published_at, content_hash, citation_label, raw_json
        ) VALUES (
          %(source_type)s, %(provider)s, %(title)s, %(url)s, %(published_at)s,
          %(content_hash)s, %(citation_label)s, %(raw_json)s::jsonb
        )
        ON CONFLICT (provider, content_hash) WHERE content_hash IS NOT NULL DO UPDATE SET
          title = EXCLUDED.title,
          url = EXCLUDED.url,
          published_at = EXCLUDED.published_at,
          citation_label = EXCLUDED.citation_label,
          raw_json = EXCLUDED.raw_json,
          fetched_at = now()
        """
        prepared = []
        for row in rows:
            source = row["source"]
            source_type = _research_source_type(source.get("kind"))
            raw_json = json_dumps(source)
            prepared.append(
                {
                    "source_type": source_type,
                    "provider": source.get("kind") or "on-demand-research",
                    "title": source.get("title") or source.get("kind") or row["target_slug"],
                    "url": source.get("url"),
                    "published_at": source.get("published_at"),
                    "content_hash": hashlib.sha256(f"{row['target_slug']}|{row['report_date']}|{raw_json}".encode("utf-8")).hexdigest(),
                    "citation_label": f"{row['target_slug']} {source_type}",
                    "raw_json": raw_json,
                }
            )
        with self.connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, prepared)
            return len(prepared)

    def record_obsidian_export(
        self,
        *,
        export_id: str,
        view_id: int | None,
        target_slug: str,
        report_date: str,
        vault_path: str,
        relative_path: str,
        file_path: str,
        file_hash: str,
        status: str,
        error_message: str | None,
    ) -> None:
        sql = """
        INSERT INTO obsidian_exports (
          export_id, view_id, target_slug, report_date, vault_path, relative_path,
          file_hash, status, error_message
        ) VALUES (
          %(export_id)s, %(view_id)s, %(target_slug)s, %(report_date)s, %(vault_path)s, %(relative_path)s,
          %(file_hash)s, %(status)s, %(error_message)s
        )
        ON CONFLICT (target_slug, report_date, relative_path) DO UPDATE SET
          view_id = EXCLUDED.view_id,
          vault_path = EXCLUDED.vault_path,
          file_hash = EXCLUDED.file_hash,
          status = EXCLUDED.status,
          error_message = EXCLUDED.error_message,
          exported_at = now()
        """
        params = {
            "export_id": export_id,
            "view_id": view_id,
            "target_slug": target_slug,
            "report_date": report_date,
            "vault_path": vault_path,
            "relative_path": relative_path,
            "file_path": file_path,
            "file_hash": file_hash,
            "status": status,
            "error_message": error_message,
        }
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)

    def fetch_latest_research_views(self, slug: str) -> dict[str, dict[str, Any]]:
        query = """
        WITH wl_assets AS (
          SELECT a.symbol
          FROM watchlists w
          JOIN watchlist_members wm ON wm.watchlist_id = w.watchlist_id
          JOIN assets a ON a.asset_id = wm.asset_id
          WHERE w.slug = %s AND a.active = TRUE
        ), latest AS (
          SELECT rv.*, row_number() OVER (PARTITION BY rv.target_slug ORDER BY rv.report_date DESC, rv.updated_at DESC) AS rn
          FROM research_views rv
          JOIN wl_assets wa ON wa.symbol = rv.target_slug
          WHERE rv.target_type = 'asset' AND rv.horizon = 'on_demand'
        )
        SELECT target_slug, opinion, thesis, rationale, bull, base, bear, risks, triggers, sources, report_date
        FROM latest WHERE rn = 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (slug,))
            views: dict[str, dict[str, Any]] = {}
            for row in cur.fetchall():
                views[row[0]] = {
                    "opinion": row[1],
                    "thesis": row[2],
                    "rationale": row[3] or [],
                    "bull": row[4],
                    "base": row[5],
                    "bear": row[6],
                    "risks": row[7] or [],
                    "triggers": row[8] or [],
                    "sources": row[9] or [],
                    "research_date": row[10],
                }
            return views

    def fetch_latest_research_for_asset(self, symbol: str) -> dict[str, Any] | None:
        query = """
        SELECT target_slug, opinion, thesis, bull, base, bear, risks, triggers, sources, report_date
        FROM research_views
        WHERE target_type = 'asset' AND target_slug = %s AND horizon = 'on_demand'
        ORDER BY report_date DESC, updated_at DESC
        LIMIT 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (symbol,))
            row = cur.fetchone()
            if row is None:
                return None
            return {
                "target_slug": row[0],
                "opinion": row[1],
                "thesis": row[2],
                "bull": row[3],
                "base": row[4],
                "bear": row[5],
                "risks": row[6] or [],
                "triggers": row[7] or [],
                "sources": row[8] or [],
                "report_date": row[9],
            }

    def generate_research_for_asset(self, auth_user_id: str, symbol: str) -> dict[str, Any]:
        profile = self.fetch_profile_by_auth_user(auth_user_id)
        if profile is None:
            raise LookupError("authenticated profile not found")
        item = self.fetch_asset_dashboard_item(symbol)
        if item is None:
            raise LookupError("asset data not found")
        history = item["history"]
        latest = history.iloc[-1].to_dict()
        packet = build_source_packet(item["asset"], latest, news=item.get("news", []), disclosures=item.get("disclosures", []))
        ai_client = build_research_ai_client_from_env(os.environ)
        row = build_on_demand_research_view(
            item["asset"],
            latest,
            packet,
            ai_credentials_present=ai_client is not None,
            model_provider=ai_client.provider_name if ai_client is not None else None,
            ai_client=ai_client,
        )
        self.upsert_research_views([row])
        self.record_report_run(
            run_type="on-demand-research",
            scope_type="asset",
            scope_slug=symbol,
            failed_assets=[],
            output_summary=f"research=1 opinion={row['opinion']}",
            output_path=None,
        )
        return row

    def fetch_asset_dashboard_item(self, symbol: str, *, days: int = 260) -> dict[str, Any] | None:
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

    def fetch_recent_news_for_asset(self, asset_id: int, *, limit: int = 10) -> list[dict[str, Any]]:
        query = """
        SELECT ni.provider, ni.source, COALESCE(ni.canonical_url, ni.url), ni.title, ni.published_at
        FROM asset_news_map anm
        JOIN news_items ni ON ni.news_id = anm.news_id
        WHERE anm.asset_id = %s
        ORDER BY ni.published_at DESC NULLS LAST, ni.news_id DESC
        LIMIT %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (asset_id, limit))
            return [
                {
                    "provider": row[0],
                    "source": row[1],
                    "url": row[2],
                    "title": row[3],
                    "published_at": row[4],
                }
                for row in cur.fetchall()
            ]

    def fetch_recent_disclosures_for_asset(self, asset_id: int, *, limit: int = 10) -> list[dict[str, Any]]:
        query = """
        SELECT provider, title, url, published_at, provider_disclosure_id
        FROM disclosures
        WHERE asset_id = %s
        ORDER BY published_at DESC NULLS LAST, disclosure_id DESC
        LIMIT %s
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (asset_id, limit))
            return [
                {
                    "provider": row[0],
                    "title": row[1],
                    "url": row[2],
                    "published_at": row[3],
                    "provider_disclosure_id": row[4],
                }
                for row in cur.fetchall()
            ]

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str) -> bool:
        query = """
        SELECT 1
        FROM profiles p
        JOIN entitlements e ON e.profile_id = p.profile_id
        WHERE p.auth_user_id = %s
          AND e.status = 'active'
          AND (e.expires_at IS NULL OR e.expires_at > now())
          AND e.entitlement_type IN ('subscriber', 'admin')
        LIMIT 1
        """
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query, (auth_user_id,))
            if cur.fetchone() is not None:
                return True
            cur.execute(
                """
                SELECT 1
                FROM profiles p
                JOIN ad_unlocks a ON a.profile_id = p.profile_id
                WHERE p.auth_user_id = %s
                  AND a.target_type = 'asset'
                  AND a.target_slug = %s
                  AND a.unlocks_until > now()
                LIMIT 1
                """,
                (auth_user_id, symbol),
            )
            return cur.fetchone() is not None

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str) -> dict[str, Any]:
        unlock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
            cur.execute(
                """
                INSERT INTO ad_unlocks (
                  ad_unlock_id,
                  profile_id,
                  provider,
                  ad_event_id,
                  target_type,
                  target_slug,
                  unlocks_until
                )
                VALUES (%s, %s, %s, %s, 'asset', %s, %s)
                ON CONFLICT (provider, ad_event_id) DO UPDATE SET
                  unlocks_until = GREATEST(ad_unlocks.unlocks_until, EXCLUDED.unlocks_until)
                RETURNING unlocks_until
                """,
                (str(uuid.uuid4()), profile_id, "local", ad_event_id, symbol, unlock_expires_at),
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO entitlements (
                  entitlement_id,
                  profile_id,
                  entitlement_type,
                  provider,
                  provider_subject_id,
                  starts_at,
                  expires_at,
                  status,
                  metadata
                )
                VALUES (%s, %s, 'ad_unlocked', 'local', %s, now(), %s, 'active', %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    profile_id,
                    ad_event_id,
                    unlock_expires_at,
                    json_dumps({"symbol": symbol, "ad_event_id": ad_event_id}),
                ),
            )
        return {
            "auth_user_id": auth_user_id,
            "target_slug": symbol,
            "entitlement_state": "ad_unlocked",
            "expires_at": row[0] if row else unlock_expires_at,
        }

    def grant_subscription_entitlement(
        self,
        auth_user_id: str,
        provider: str,
        provider_subject_id: str,
    ) -> dict[str, Any]:
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = self._ensure_profile(cur, auth_user_id)
            cur.execute(
                """
                INSERT INTO entitlements (
                  entitlement_id,
                  profile_id,
                  entitlement_type,
                  provider,
                  provider_subject_id,
                  starts_at,
                  expires_at,
                  status,
                  metadata
                )
                VALUES (%s, %s, 'subscriber', %s, %s, now(), NULL, 'active', %s::jsonb)
                ON CONFLICT DO NOTHING
                RETURNING starts_at
                """,
                (
                    str(uuid.uuid4()),
                    profile_id,
                    provider,
                    provider_subject_id,
                    json_dumps({"provider_subject_id": provider_subject_id}),
                ),
            )
            cur.fetchone()
        return {
            "auth_user_id": auth_user_id,
            "target_slug": None,
            "entitlement_state": "subscriber",
            "expires_at": None,
        }

    def record_payment_webhook(
        self,
        event_id: str,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
        signature_valid: bool,
    ) -> dict[str, Any]:
        with self.connect() as conn, conn.cursor() as cur:
            profile_id = None
            auth_user_id = payload.get("auth_user_id")
            if isinstance(auth_user_id, str) and auth_user_id:
                cur.execute("SELECT profile_id FROM profiles WHERE auth_user_id = %s LIMIT 1", (auth_user_id,))
                profile_row = cur.fetchone()
                profile_id = None if profile_row is None else profile_row[0]
            cur.execute(
                """
                INSERT INTO payment_webhook_events (
                  event_id,
                  provider,
                  event_type,
                  profile_id,
                  status,
                  signature_valid,
                  raw_json
                )
                VALUES (%s, %s, %s, %s, 'received', %s, %s::jsonb)
                ON CONFLICT (provider, event_id) DO NOTHING
                RETURNING event_id
                """,
                (event_id, provider, event_type, profile_id, signature_valid, json_dumps(payload)),
            )
            inserted = cur.fetchone()
            if inserted is None:
                return {"status": "ignored", "duplicate": True}
            cur.execute(
                """
                UPDATE payment_webhook_events
                SET status = 'processed', processed_at = now()
                WHERE provider = %s AND event_id = %s
                """,
                (provider, event_id),
            )
        return {"status": "processed", "duplicate": False}

    def _ensure_profile(self, cur, auth_user_id: str) -> int:
        slug = f"user-{hashlib_sha(auth_user_id)[:12]}"
        cur.execute(
            """
            INSERT INTO profiles (slug, name, auth_user_id, auth_provider)
            VALUES (%s, %s, %s, 'local-test')
            ON CONFLICT (auth_user_id) WHERE auth_user_id IS NOT NULL DO UPDATE SET updated_at = now()
            RETURNING profile_id
            """,
            (slug, slug, auth_user_id),
        )
        return cur.fetchone()[0]

    def _ensure_asset(self, cur, symbol: str) -> int:
        cur.execute(
            """
            INSERT INTO assets (symbol, exchange, currency)
            VALUES (%s, NULL, NULL)
            ON CONFLICT (symbol) DO UPDATE SET updated_at = now()
            RETURNING asset_id
            """,
            (symbol,),
        )
        return cur.fetchone()[0]

    def _watchlist_slug(self, auth_user_id: str, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "watchlist"
        return f"{hashlib_sha(auth_user_id)[:12]}-{base}"


def hashlib_sha(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
