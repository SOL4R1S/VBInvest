"""VBinvestDB — composed from domain mixins.

Original monolith split into:
  db_base.py        — shared helpers (json_dumps, build_price_rows, etc.)
  db_marketdata.py  — MarketDataMixin (prices, indicators, dashboards)
  db_user.py        — UserMixin (profiles, watchlists)
  db_ingest.py      — IngestMixin (news, disclosures, report runs, locks)
  db_research.py    — ResearchMixin (research views, sources, exports)
  db_entitlement.py — EntitlementMixin (ad unlocks, subscriptions, webhooks)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote_plus

from scripts.lib.keychain import SecretStore, resolve_secret
from scripts.lib.db_base import (
    build_indicator_rows,
    build_price_rows,
    hashlib_sha,
    json_dumps,
    none_if_na,
    _profile_slug,
)
from scripts.lib.db_marketdata import MarketDataMixin
from scripts.lib.db_user import UserMixin
from scripts.lib.db_ingest import IngestMixin
from scripts.lib.db_research import ResearchMixin
from scripts.lib.db_entitlement import EntitlementMixin


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    host: str = "host.docker.internal"
    port: int = 5432
    database: str = "vbinvest"
    user: str = "vbinvest"
    password: str = ""

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        system_name: str | None = None,
        secret_store: SecretStore | None = None,
    ) -> "DatabaseConfig":
        return cls(
            host=env.get("VBINVEST_DB_HOST") or env.get("POSTGRES_HOST") or "host.docker.internal",
            port=int(env.get("VBINVEST_DB_PORT") or env.get("POSTGRES_PORT") or 5432),
            database=env.get("VBINVEST_DB_NAME") or env.get("POSTGRES_DB") or "vbinvest",
            user=env.get("VBINVEST_DB_USER") or env.get("POSTGRES_USER") or "vbinvest",
            password=resolve_secret(
                env,
                "POSTGRES_PASSWORD",
                aliases=("VBINVEST_DB_PASSWORD",),
                system_name=system_name,
                store=secret_store,
            ),
        )

    def dsn(self, *, mask_password: bool = True) -> str:
        user = quote_plus(self.user)
        password = "***" if mask_password and self.password else quote_plus(self.password)
        auth = user if not self.password else f"{user}:{password}"
        return f"postgresql://{auth}@{self.host}:{self.port}/{quote_plus(self.database)}"

    def safe_summary(self) -> str:
        password_state = "***" if self.password else "<unset>"
        return (
            f"host={self.host} port={self.port} database={self.database} "
            f"user={self.user} password={password_state}"
        )


class VBinvestDB(MarketDataMixin, UserMixin, IngestMixin, ResearchMixin, EntitlementMixin):
    """PostgreSQL-backed data store composed from domain mixins."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._settings_metadata_ready = False
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for live DB access") from exc
        self._psycopg = psycopg

    @classmethod
    def from_local_config(
        cls,
        *,
        config_path: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        from scripts.lib.db_factory import build_database_from_local_config

        return build_database_from_local_config(config_path=config_path, environ=environ)
    def connect(self):
        return self._psycopg.connect(self.config.dsn(mask_password=False))
