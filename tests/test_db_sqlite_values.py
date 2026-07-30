"""Tests for scripts.lib.db_sqlite_values — JSON/date coercion helpers."""

from datetime import UTC, date, datetime

from scripts.lib.db_sqlite_values import SQLiteValueMixin, json_loads_list

# ---------------------------------------------------------------------------
# json_loads_list
# ---------------------------------------------------------------------------


def test_json_loads_list_valid():
    assert json_loads_list("[1, 2, 3]") == [1, 2, 3]


def test_json_loads_list_none():
    assert json_loads_list(None) == []


def test_json_loads_list_empty():
    assert json_loads_list("") == []


def test_json_loads_list_invalid_json():
    assert json_loads_list("not json") == []


def test_json_loads_list_not_a_list():
    assert json_loads_list('{"a": 1}') == []


# ---------------------------------------------------------------------------
# SQLiteValueMixin date/timestamp coercion
# ---------------------------------------------------------------------------


class _FakeDB(SQLiteValueMixin):
    pass


def test_to_db_date_datetime():
    db = _FakeDB()
    dt = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
    assert db._to_db_date(dt) == "2026-03-15"


def test_to_db_date_date():
    db = _FakeDB()
    d = date(2026, 3, 15)
    assert db._to_db_date(d) == "2026-03-15"


def test_to_db_date_passthrough():
    db = _FakeDB()
    assert db._to_db_date("2026-03-15") == "2026-03-15"
    assert db._to_db_date(42) == 42


def test_to_db_timestamp_datetime():
    db = _FakeDB()
    dt = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
    result = db._to_db_timestamp(dt)
    assert "2026-03-15" in result
    assert "+00:00" in result


def test_to_db_timestamp_date():
    db = _FakeDB()
    d = date(2026, 3, 15)
    result = db._to_db_timestamp(d)
    assert "2026-03-15" in result


def test_to_db_timestamp_passthrough():
    db = _FakeDB()
    assert db._to_db_timestamp("already-a-string") == "already-a-string"


def test_coerce_datetime_naive():
    db = _FakeDB()
    dt = datetime(2026, 3, 15, 10, 30)
    result = db._coerce_datetime(dt)
    assert result is not None
    assert result.tzinfo == UTC


def test_coerce_datetime_aware():
    db = _FakeDB()
    dt = datetime(2026, 3, 15, 10, 30, tzinfo=UTC)
    result = db._coerce_datetime(dt)
    assert result == dt


def test_coerce_datetime_string():
    db = _FakeDB()
    result = db._coerce_datetime("2026-03-15T10:30:00+00:00")
    assert result is not None
    assert result.year == 2026
    assert result.tzinfo == UTC


def test_coerce_datetime_invalid_string():
    db = _FakeDB()
    assert db._coerce_datetime("not-a-date") is None


def test_coerce_datetime_none():
    db = _FakeDB()
    assert db._coerce_datetime(None) is None
    assert db._coerce_datetime(42) is None
