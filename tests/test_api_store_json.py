"""Tests for scripts.lib.api_store — json_dumps utility."""

import json
from datetime import date, datetime

from scripts.lib.api_store import json_dumps


class TestJsonDumps:
    def test_none_becomes_empty_object(self):
        assert json_dumps(None) == "{}"

    def test_dict_passthrough(self):
        result = json_dumps({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_ensure_ascii_false(self):
        result = json_dumps({"name": "한글"})
        assert "한글" in result

    def test_datetime_serialized_as_string(self):
        dt = datetime(2024, 6, 15, 12, 30, 0)
        result = json_dumps({"ts": dt})
        parsed = json.loads(result)
        assert "2024-06-15" in parsed["ts"]

    def test_date_serialized_as_string(self):
        d = date(2024, 6, 15)
        result = json_dumps({"d": d})
        parsed = json.loads(result)
        assert parsed["d"] == "2024-06-15"

    def test_nested_structure(self):
        data = {"a": [1, 2], "b": {"c": True}}
        result = json_dumps(data)
        assert json.loads(result) == data

    def test_empty_dict(self):
        assert json_dumps({}) == "{}"

    def test_list_input(self):
        result = json_dumps([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]
