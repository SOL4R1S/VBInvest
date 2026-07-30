"""Integration tests for SQLiteSourcesMixin — disclosures upsert, news edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.db_sqlite import SQLiteVBinvestDB


@pytest.fixture()
def db(tmp_path: Path) -> SQLiteVBinvestDB:
    return SQLiteVBinvestDB(tmp_path / "test.db")


@pytest.fixture()
def asset_id(db: SQLiteVBinvestDB) -> int:
    assets = db.ensure_assets_for_refresh([{"symbol": "AAPL", "display_name_ko": "애플"}])
    return assets[0]["asset_id"]


class TestUpsertDisclosures:
    def test_empty(self, db: SQLiteVBinvestDB):
        assert db.upsert_disclosures([]) == 0

    def test_insert_single(self, db: SQLiteVBinvestDB, asset_id: int):
        rows = [
            {
                "asset_id": asset_id,
                "market": "US",
                "provider": "sec",
                "provider_disclosure_id": "disc-001",
                "title": "10-K Filing",
                "published_at": "2026-01-15T09:00:00Z",
                "url": "https://sec.gov/filing/001",
                "raw_json": {"type": "10-K"},
            }
        ]
        assert db.upsert_disclosures(rows) == 1

    def test_insert_multiple(self, db: SQLiteVBinvestDB, asset_id: int):
        rows = [
            {
                "asset_id": asset_id,
                "market": "US",
                "provider": "sec",
                "provider_disclosure_id": f"disc-{i:03d}",
                "title": f"Filing {i}",
                "published_at": "2026-01-15T09:00:00Z",
                "url": f"https://sec.gov/filing/{i:03d}",
                "raw_json": None,
            }
            for i in range(5)
        ]
        assert db.upsert_disclosures(rows) == 5

    def test_upsert_overwrites_on_conflict(self, db: SQLiteVBinvestDB, asset_id: int):
        row = {
            "asset_id": asset_id,
            "market": "US",
            "provider": "sec",
            "provider_disclosure_id": "disc-dup",
            "title": "Original Title",
            "published_at": "2026-01-15T09:00:00Z",
            "url": "https://sec.gov/filing/dup",
            "raw_json": None,
        }
        db.upsert_disclosures([row])
        updated = {**row, "title": "Updated Title"}
        assert db.upsert_disclosures([updated]) == 1

    def test_null_provider_disclosure_id(self, db: SQLiteVBinvestDB, asset_id: int):
        rows = [
            {
                "asset_id": asset_id,
                "market": "KR",
                "provider": "dart",
                "provider_disclosure_id": None,
                "title": "DART Filing",
                "published_at": "2026-01-15T09:00:00Z",
                "url": "https://dart.fss.or.kr/filing/1",
                "raw_json": None,
            }
        ]
        assert db.upsert_disclosures(rows) == 1


class TestUpsertNewsItemsEdgeCases:
    def test_canonical_url_dedup(self, db: SQLiteVBinvestDB, asset_id: int):
        row = {
            "asset_id": asset_id,
            "provider": "reuters",
            "source": "reuters",
            "source_id": None,
            "url": "https://reuters.com/article/1",
            "canonical_url": "https://reuters.com/article/1",
            "title": "Test Article",
            "published_at": "2026-01-15T10:00:00Z",
            "content_hash": None,
            "language": "en",
            "summary": "Test summary",
            "raw_json": None,
            "relevance": 0.9,
        }
        count1 = db.upsert_news_items([row])
        assert count1 == 1
        # Same canonical_url → dedup
        count2 = db.upsert_news_items([row])
        assert count2 == 1

    def test_content_hash_dedup(self, db: SQLiteVBinvestDB, asset_id: int):
        row = {
            "asset_id": asset_id,
            "provider": "bloomberg",
            "source": "bloomberg",
            "source_id": None,
            "url": "https://bloomberg.com/news/1",
            "canonical_url": None,
            "title": "Hash Article",
            "published_at": "2026-01-15T11:00:00Z",
            "content_hash": "hash-abc-123",
            "language": "en",
            "summary": "Hash summary",
            "raw_json": None,
            "relevance": 0.7,
        }
        count1 = db.upsert_news_items([row])
        assert count1 == 1
        count2 = db.upsert_news_items([row])
        assert count2 == 1

    def test_multiple_assets_same_news(self, db: SQLiteVBinvestDB):
        assets = db.ensure_assets_for_refresh(
            [
                {"symbol": "AAPL", "display_name_ko": "애플"},
                {"symbol": "MSFT", "display_name_ko": "마이크로소프트"},
            ]
        )
        aapl_id = assets[0]["asset_id"]
        msft_id = assets[1]["asset_id"]
        row_aapl = {
            "asset_id": aapl_id,
            "provider": "cnbc",
            "source": "cnbc",
            "source_id": "cnbc-001",
            "url": "https://cnbc.com/tech",
            "canonical_url": "https://cnbc.com/tech",
            "title": "Tech News",
            "published_at": "2026-01-15T12:00:00Z",
            "content_hash": None,
            "language": "en",
            "summary": "Tech summary",
            "raw_json": None,
            "relevance": 0.8,
        }
        row_msft = {
            **row_aapl,
            "asset_id": msft_id,
            "source_id": "cnbc-002",
            "canonical_url": "https://cnbc.com/tech-msft",
        }
        count = db.upsert_news_items([row_aapl, row_msft])
        assert count == 2
