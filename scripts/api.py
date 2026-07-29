"""VBinvest API application.

Thin app module: imports routers and wires them into a single FastAPI app.
All route handlers live in scripts/routers/*.py.
"""

from __future__ import annotations

import shutil  # noqa: F401 — kept for test monkeypatching (test_first_run_setup_api)
import sys
from pathlib import Path
from typing import Callable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI

from scripts.lib.version import load_version_metadata
from scripts.routers import frontend, portfolio, research, scheduler, settings, watchlists

VERSION_METADATA = load_version_metadata()

app = FastAPI(title="VBinvest API", version=VERSION_METADATA.version)

ShutdownCallback = Callable[[], None]
LOCAL_SHUTDOWN_CALLBACK: ShutdownCallback | None = None

# Register routers (order matters: catch-all last)
app.include_router(settings.router)
app.include_router(scheduler.router)
app.include_router(watchlists.router)
app.include_router(portfolio.router)
app.include_router(research.router)
app.include_router(frontend.router)  # catch-all /{asset_path:path} must be last
