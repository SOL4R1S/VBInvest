"""VBinvestDB ResearchMixin — extracted from db.py."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from scripts.lib.db_base import _research_source_type, json_dumps
from scripts.lib.db_mixin_base import DBMixinBase
from scripts.lib.on_demand_report import OnDemandReportStore, generate_on_demand_research_for_asset


class ResearchMixin(DBMixinBase):
    """Mixin — requires self.connect() from VBinvestDB."""

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
                    "content_hash": hashlib.sha256(
                        f"{row['target_slug']}|{row['report_date']}|{raw_json}".encode()
                    ).hexdigest(),
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

    def generate_research_for_asset(
        self,
        auth_user_id: str,
        symbol: str,
        *,
        obsidian_vault_path: str | Path | None = None,
    ) -> dict[str, Any]:
        return generate_on_demand_research_for_asset(
            cast(OnDemandReportStore, self),
            auth_user_id,
            symbol,
            obsidian_vault_path=obsidian_vault_path,
        )

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
