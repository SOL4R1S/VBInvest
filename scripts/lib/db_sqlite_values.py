from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any


def json_loads_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


class SQLiteValueMixin:
    def _to_db_date(self, value: Any) -> str | Any:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    def _to_db_timestamp(self, value: Any) -> str | Any:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).isoformat()
        return value

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return None
            return self._coerce_datetime(parsed)
        return None
