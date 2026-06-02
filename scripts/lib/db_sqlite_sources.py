from __future__ import annotations

from typing import Any

from scripts.lib.db import json_dumps


class SQLiteSourcesMixin:
    def upsert_news_items(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        count = 0
        with self.connect() as conn:
            for row in rows:
                params = dict(row)
                raw_json = json_dumps(params.get("raw_json"))
                content_hash = params.get("content_hash")
                source_id = params.get("source_id")
                canonical_url = params.get("canonical_url")
                if source_id:
                    conflict_target = "provider, source_id"
                    conflict_where = "source_id"
                elif canonical_url:
                    conflict_target = "canonical_url"
                    conflict_where = "canonical_url"
                else:
                    conflict_target = "provider, content_hash"
                    conflict_where = "content_hash"
                conn.execute(
                    f"""
                    INSERT INTO news_items (
                      provider, source, source_id, url, canonical_url, title, published_at,
                      content_hash, language, summary, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT ({conflict_target}) DO UPDATE SET
                      source = excluded.source,
                      url = excluded.url,
                      canonical_url = excluded.canonical_url,
                      title = excluded.title,
                      published_at = excluded.published_at,
                      content_hash = excluded.content_hash,
                      language = excluded.language,
                      summary = excluded.summary,
                      raw_json = excluded.raw_json,
                      updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        params.get("provider"),
                        params.get("source"),
                        source_id,
                        params.get("url"),
                        canonical_url,
                        params.get("title"),
                        self._to_db_timestamp(params.get("published_at")),
                        content_hash,
                        params.get("language"),
                        params.get("summary"),
                        raw_json,
                    ),
                )
                news_row = self._fetch_news_row(conn, params, conflict_where)
                if news_row is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO asset_news_map (asset_id, news_id, relevance)
                    VALUES (?, ?, ?)
                    ON CONFLICT (asset_id, news_id) DO UPDATE SET relevance = excluded.relevance
                    """,
                    (params["asset_id"], news_row["news_id"], params.get("relevance")),
                )
                count += 1
        return count

    def upsert_disclosures(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO disclosures (
                  asset_id, market, provider, provider_disclosure_id, title, published_at, url, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (provider, provider_disclosure_id) DO UPDATE SET
                  asset_id = excluded.asset_id,
                  market = excluded.market,
                  title = excluded.title,
                  published_at = excluded.published_at,
                  url = excluded.url,
                  raw_json = excluded.raw_json,
                  updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        row.get("asset_id"),
                        row.get("market"),
                        row.get("provider"),
                        row.get("provider_disclosure_id"),
                        row.get("title"),
                        self._to_db_timestamp(row.get("published_at")),
                        row.get("url"),
                        json_dumps(row.get("raw_json")),
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def _fetch_news_row(self, conn, params: dict[str, Any], conflict_where: str):
        match conflict_where:
            case "source_id":
                return conn.execute(
                    "SELECT news_id FROM news_items WHERE provider = ? AND source_id = ? ORDER BY news_id DESC LIMIT 1",
                    (params.get("provider"), params.get("source_id")),
                ).fetchone()
            case "canonical_url":
                return conn.execute(
                    "SELECT news_id FROM news_items WHERE canonical_url = ? ORDER BY news_id DESC LIMIT 1",
                    (params.get("canonical_url"),),
                ).fetchone()
            case "content_hash":
                return conn.execute(
                    "SELECT news_id FROM news_items WHERE provider = ? AND content_hash = ? ORDER BY news_id DESC LIMIT 1",
                    (params.get("provider"), params.get("content_hash")),
                ).fetchone()
            case _:
                raise ValueError("unknown news conflict selector")
