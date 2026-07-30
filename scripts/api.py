"""VBinvest API application.

Thin app module: imports routers and wires them into a single FastAPI app.
All route handlers live in scripts/routers/*.py.
"""

from __future__ import annotations

import os
import shutil  # noqa: F401 — kept for test monkeypatching (test_first_run_setup_api)
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI

from scripts.lib.api_store import ApiStore
from scripts.lib.config import load_opendart_api_key  # noqa: F401 — re-exported for tests
from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.db_repository import DBRepository
from scripts.lib.disclosures import check_opendart_api_key  # noqa: F401 — re-exported for tests
from scripts.lib.prices import search_ticker_suggestions, validate_ticker_symbol  # noqa: F401 — re-exported for tests
from scripts.lib.ticker_catalog import refresh_ticker_catalog  # noqa: F401 — re-exported for tests
from scripts.lib.version import load_version_metadata
from scripts.routers import frontend, portfolio, research, scheduler, settings, watchlists

try:
    from psycopg import OperationalError as PostgresOperationalError
except ImportError:
    PostgresOperationalError = RuntimeError  # type: ignore[assignment,misc]

VERSION_METADATA = load_version_metadata()

app = FastAPI(title="VBinvest API", version=VERSION_METADATA.version)

ShutdownCallback = Callable[[], None]
LOCAL_SHUTDOWN_CALLBACK: ShutdownCallback | None = None


def db() -> DBRepository:
    """Module-level db accessor — tests monkeypatch this via api.db."""
    return build_database_from_local_config(environ=os.environ)


def auth_db():
    """Auth-aware DB wrapper — tests monkeypatch this via api.auth_db."""
    backend = db()
    if hasattr(backend, "fetch_profile_by_auth_user"):
        return backend
    return ApiStore(backend)


def frontend_out_dir() -> Path:
    """Frontend build output directory — tests monkeypatch this via api.frontend_out_dir."""
    configured = os.environ.get("VBINVEST_FRONTEND_OUT_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "frontend" / "out"


def check_postgres_url(postgres_url: str) -> bool:
    """Verify a PostgreSQL connection string is reachable."""
    try:
        import psycopg
    except ImportError:
        return False
    try:
        with psycopg.connect(postgres_url, connect_timeout=3):
            return True
    except PostgresOperationalError:
        return False


# Register routers (order matters: catch-all last)
app.include_router(settings.router)
app.include_router(scheduler.router)
app.include_router(watchlists.router)
app.include_router(portfolio.router)
app.include_router(research.router)
app.include_router(frontend.router)  # catch-all /{asset_path:path} must be last
