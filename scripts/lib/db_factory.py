from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlsplit

from scripts.lib.config import DatabaseMode, load_local_config
from scripts.lib.db import DatabaseConfig, VBinvestDB
from scripts.lib.db_repository import DBRepository
from scripts.lib.db_sqlite import SQLiteVBinvestDB


def build_database_from_local_config(
    *,
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> DBRepository:
    env = os.environ if environ is None else environ
    config = load_local_config(config_path=config_path, environ=env)
    mode = config.database.mode
    if mode is DatabaseMode.SQLITE:
        return SQLiteVBinvestDB(config.database.sqlite_path)
    if mode is DatabaseMode.POSTGRES_URL:
        return VBinvestDB(_database_config_from_url(config.database.postgres_url))
    return VBinvestDB(DatabaseConfig.from_env(env))


def _database_config_from_url(url: str) -> DatabaseConfig:
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("database.postgres_url must use postgresql://")
    host = parsed.hostname or "127.0.0.1"
    port = 5432 if parsed.port is None else parsed.port
    database = parsed.path.lstrip("/") or "vbinvest"
    user = unquote(parsed.username or "vbinvest")
    password = unquote(parsed.password or "")
    return DatabaseConfig(host=host, port=port, database=database, user=user, password=password)
