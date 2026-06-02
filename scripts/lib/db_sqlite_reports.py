from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from scripts.lib.db import json_dumps
from scripts.lib.db_sqlite_values import json_loads_list


class SQLiteReportsMixin:
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
        completed_at = datetime.now(timezone.utc)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO report_runs (
                  run_id, run_type, scope_type, scope_slug, completed_at, status,
                  failed_assets, output_summary, output_path, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_type,
                    scope_type,
                    scope_slug,
                    self._to_db_timestamp(completed_at),
                    status,
                    json.dumps(failed_assets or [], ensure_ascii=False),
                    output_summary,
                    output_path,
                    error_message,
                ),
            )
        return run_id

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        return self._fetch_latest_report_run(run_type, scope_slug, successful_only=False)

    def fetch_latest_successful_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        return self._fetch_latest_report_run(run_type, scope_slug, successful_only=True)

    def upsert_research_views(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO research_views (
                  target_type, target_slug, report_date, horizon, opinion, thesis,
                  rationale, bull, base, bear, risks, triggers, sources,
                  confidence, source_freshness_status, access_tier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (target_type, target_slug, report_date, horizon) DO UPDATE SET
                  opinion = excluded.opinion,
                  thesis = excluded.thesis,
                  rationale = excluded.rationale,
                  bull = excluded.bull,
                  base = excluded.base,
                  bear = excluded.bear,
                  risks = excluded.risks,
                  triggers = excluded.triggers,
                  sources = excluded.sources,
                  confidence = excluded.confidence,
                  source_freshness_status = excluded.source_freshness_status,
                  access_tier = excluded.access_tier,
                  updated_at = CURRENT_TIMESTAMP
                """,
                [self._research_view_params(row) for row in rows],
            )
        return len(rows)

    def fetch_latest_research_for_asset(self, symbol: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT target_slug, opinion, thesis, bull, base, bear, risks, triggers, sources, report_date
                FROM research_views
                WHERE target_type = 'asset' AND target_slug = ? AND horizon = 'on_demand'
                ORDER BY report_date DESC, updated_at DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        return {
            "target_slug": row["target_slug"],
            "opinion": row["opinion"],
            "thesis": row["thesis"],
            "bull": row["bull"],
            "base": row["base"],
            "bear": row["bear"],
            "risks": json_loads_list(row["risks"]),
            "triggers": json_loads_list(row["triggers"]),
            "sources": json_loads_list(row["sources"]),
            "report_date": row["report_date"],
        }

    def _fetch_latest_report_run(self, run_type: str, scope_slug: str | None, *, successful_only: bool) -> dict[str, Any] | None:
        status_clause = "AND status = 'ok'" if successful_only else ""
        with self.connect() as conn:
            row = conn.execute(
                f"""
                SELECT run_id, run_type, scope_type, scope_slug, completed_at, status, failed_assets, output_summary, output_path, error_message
                FROM report_runs
                WHERE run_type = ? {status_clause} AND (scope_slug IS ? OR scope_slug = ?)
                ORDER BY completed_at DESC, run_id DESC
                LIMIT 1
                """,
                (run_type, scope_slug, scope_slug),
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "run_type": row["run_type"],
            "scope_type": row["scope_type"],
            "scope_slug": row["scope_slug"],
            "completed_at": self._coerce_datetime(row["completed_at"]),
            "status": row["status"],
            "failed_assets": json_loads_list(row["failed_assets"]),
            "output_summary": row["output_summary"],
            "output_path": row["output_path"],
            "error_message": row["error_message"],
        }

    def _research_view_params(self, row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row["target_type"],
            row["target_slug"],
            self._to_db_date(row["report_date"]),
            row.get("horizon") or "on_demand",
            row.get("opinion"),
            row.get("thesis"),
            json_dumps(row.get("rationale")),
            row.get("bull"),
            row.get("base"),
            row.get("bear"),
            json_dumps(row.get("risks")),
            json_dumps(row.get("triggers")),
            json_dumps(row.get("sources")),
            row.get("confidence"),
            row.get("source_freshness_status") or "unknown",
            row.get("access_tier") or "free",
        )
