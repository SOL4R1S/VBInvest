from datetime import datetime, timezone

from scripts.lib.news import dedupe_news_rows, parse_yahoo_rss, prepare_news_rows


def test_parse_yahoo_rss_normalizes_items():
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<rss><channel><item>"
        "<guid>abc-1</guid>"
        "<title>NVDA expands AI chip supply</title>"
        "<link>https://finance.yahoo.com/news/nvda-ai-chip-supply-123.html?utm_source=test</link>"
        "<pubDate>Mon, 01 Jun 2026 08:00:00 GMT</pubDate>"
        "<description>Short summary</description>"
        "</item></channel></rss>"
    )

    items = parse_yahoo_rss("NVDA", payload)

    assert len(items) == 1
    assert items[0]["provider"] == "yahoo-rss"
    assert items[0]["source_id"] == "abc-1"
    assert items[0]["canonical_url"] == "https://finance.yahoo.com/news/nvda-ai-chip-supply-123.html"
    assert items[0]["language"] == "en"
    assert items[0]["published_at"] == datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)


def test_news_upsert_is_idempotent():
    rows = prepare_news_rows(
        42,
        [
            {
                "provider": "yahoo-rss",
                "source": "Yahoo Finance",
                "source_id": "abc-1",
                "url": "https://example.com/news?id=1",
                "canonical_url": "https://example.com/news",
                "title": "Same item",
                "published_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "language": "en",
                "summary": "A",
                "raw_json": {"id": 1},
            },
            {
                "provider": "yahoo-rss",
                "source": "Yahoo Finance",
                "source_id": "abc-1",
                "url": "https://example.com/news?id=1",
                "canonical_url": "https://example.com/news",
                "title": "Same item",
                "published_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "language": "en",
                "summary": "A",
                "raw_json": {"id": 1},
            },
        ],
    )

    deduped = dedupe_news_rows(rows)

    assert len(deduped) == 1
    assert deduped[0]["asset_id"] == 42
    assert deduped[0]["content_hash"]
