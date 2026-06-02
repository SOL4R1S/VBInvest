from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.lib.db_sqlite_identity import SQLiteIdentityMixin
from scripts.lib.db_sqlite_market import SQLiteMarketMixin
from scripts.lib.db_sqlite_reports import SQLiteReportsMixin
from scripts.lib.db_sqlite_schema import SQLITE_SCHEMA
from scripts.lib.db_sqlite_sources import SQLiteSourcesMixin
from scripts.lib.db_sqlite_values import SQLiteValueMixin


class SQLiteVBinvestDB(
    SQLiteIdentityMixin,
    SQLiteMarketMixin,
    SQLiteSourcesMixin,
    SQLiteReportsMixin,
    SQLiteValueMixin,
):
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path.expanduser()
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SQLITE_SCHEMA)
