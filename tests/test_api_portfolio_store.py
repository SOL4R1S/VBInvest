"""Tests for scripts.lib.api_portfolio_store — pure helpers."""

from decimal import Decimal

from scripts.lib.api_portfolio_store import _holding_row, _json_number


class TestJsonNumber:
    def test_none_returns_none(self):
        assert _json_number(None) is None

    def test_decimal_converted_to_float(self):
        result = _json_number(Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_int_passthrough(self):
        assert _json_number(42) == 42

    def test_float_passthrough(self):
        assert _json_number(3.14) == 3.14

    def test_zero_decimal(self):
        assert _json_number(Decimal("0")) == 0.0


class TestHoldingRow:
    def test_full_row(self):
        row = ("id-1", "NVDA", 10.0, 150.5, "AI stock")
        result = _holding_row(row)
        assert result == {
            "holding_id": "id-1",
            "symbol": "NVDA",
            "quantity": 10.0,
            "average_cost": 150.5,
            "note": "AI stock",
        }

    def test_none_cost(self):
        row = ("id-2", "AAPL", 5.0, None, None)
        result = _holding_row(row)
        assert result["average_cost"] is None
        assert result["note"] is None

    def test_decimal_cost(self):
        row = ("id-3", "TSLA", Decimal("2.5"), Decimal("250.00"), "EV")
        result = _holding_row(row)
        assert result["quantity"] == 2.5
        assert result["average_cost"] == 250.0
