"""VBinvestDB IngestMixin — extracted from db.py."""

from __future__ import annotations

import json
import uuid
from typing import Any

from scripts.lib.db_base import json_dumps


class IngestMixin:

    """Mixin — requires self.connect() from VBinvestDB."""


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


    def fetch_setting(self, key: str) -> str | None:
        self._ensure_settings_metadata()
        sql = "SELECT value FROM settings_metadata WHERE key = %s"
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (key,))
            row = cur.fetchone()
        return None if row is None else row[0]


    def upsert_setting(self, key: str, value: str) -> None:
        self._ensure_settings_metadata()
        sql = "INSERT INTO settings_metadata (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (key, value))


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


    def cancel_report_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE report_runs
                SET status = 'canceled', error_message = 'canceled by user'
                WHERE run_id = %s AND status IN ('queued', 'running')
                """,
                (run_id,),
            )
            cur.execute(
                """
                SELECT run_id, run_type, scope_type, scope_slug, completed_at, status, failed_assets, output_summary, output_path, error_message
                FROM report_runs
                WHERE run_id = %s
                LIMIT 1
                """,
                (run_id,),
            )
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


    def _ensure_settings_metadata(self) -> None:
        if self._settings_metadata_ready:
            return
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings_metadata (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """
            )
        self._settings_metadata_ready = True
