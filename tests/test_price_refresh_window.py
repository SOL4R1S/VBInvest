"""Tests for scripts.lib.price_refresh_window — window calculation logic."""

from datetime import date, timedelta

import pandas as pd

from scripts.lib.price_refresh_window import (
    INITIAL_BACKFILL_DAYS,
    INDICATOR_LOOKBACK_DAYS,
    PriceDateRange,
    PriceRefreshWindow,
    filter_history_for_persistence,
    price_refresh_window,
    run_date_from_fetched_at,
)


# ---------------------------------------------------------------------------
# run_date_from_fetched_at
# ---------------------------------------------------------------------------


def test_run_date_from_fetched_at_explicit():
    from datetime import UTC, datetime

    dt = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
    assert run_date_from_fetched_at(dt) == date(2026, 3, 15)


def test_run_date_from_fetched_at_none():
    result = run_date_from_fetched_at(None)
    assert isinstance(result, date)


# ---------------------------------------------------------------------------
# price_refresh_window
# ---------------------------------------------------------------------------


def test_window_no_history():
    run = date(2026, 6, 1)
    window = price_refresh_window(None, run)
    expected_start = run - timedelta(days=INITIAL_BACKFILL_DAYS)
    assert window.fetch_start == expected_start
    assert window.persist_start == expected_start
    assert window.end == run


def test_window_with_history():
    run = date(2026, 6, 1)
    latest = date(2026, 5, 20)
    window = price_refresh_window(latest, run)
    assert window.persist_start == latest + timedelta(days=1)
    assert window.fetch_start == window.persist_start - timedelta(days=INDICATOR_LOOKBACK_DAYS)
    assert window.end == run


def test_window_early_earliest_triggers_full_backfill():
    run = date(2026, 6, 1)
    latest = date(2026, 5, 20)
    # earliest_date is AFTER backfill_start → full backfill
    backfill_start = run - timedelta(days=INITIAL_BACKFILL_DAYS)
    early_earliest = backfill_start + timedelta(days=10)
    window = price_refresh_window(latest, run, earliest_date=early_earliest)
    assert window.fetch_start == backfill_start
    assert window.persist_start == backfill_start


def test_window_old_earliest_incremental():
    run = date(2026, 6, 1)
    latest = date(2026, 5, 20)
    backfill_start = run - timedelta(days=INITIAL_BACKFILL_DAYS)
    old_earliest = backfill_start - timedelta(days=10)
    window = price_refresh_window(latest, run, earliest_date=old_earliest)
    assert window.persist_start == latest + timedelta(days=1)


# ---------------------------------------------------------------------------
# filter_history_for_persistence
# ---------------------------------------------------------------------------


def test_filter_history_none_window():
    frame = pd.DataFrame({"date": ["2026-01-01"], "close": [100]})
    result = filter_history_for_persistence(frame, None)
    assert len(result) == 1


def test_filter_history_filters():
    window = PriceRefreshWindow(
        fetch_start=date(2026, 1, 1),
        persist_start=date(2026, 3, 1),
        end=date(2026, 6, 1),
    )
    frame = pd.DataFrame(
        {
            "date": ["2026-01-15", "2026-03-15", "2026-05-01", "2026-07-01"],
            "close": [100, 200, 300, 400],
        }
    )
    result = filter_history_for_persistence(frame, window)
    assert len(result) == 2
    assert list(result["close"]) == [200, 300]


def test_filter_history_empty_frame():
    window = PriceRefreshWindow(
        fetch_start=date(2026, 1, 1),
        persist_start=date(2026, 3, 1),
        end=date(2026, 6, 1),
    )
    frame = pd.DataFrame({"date": [], "close": []})
    result = filter_history_for_persistence(frame, window)
    assert result.empty
