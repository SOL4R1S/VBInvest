"""Health, system, frontend serving, and catch-all routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.version import load_version_metadata
from scripts.routers.deps import (
    ShutdownBeaconPayload,
    current_user,
    db,
)

router = APIRouter()

VERSION_METADATA = load_version_metadata()


def _frontend_out_dir():
    """Delegate to api.frontend_out_dir so tests can monkeypatch it."""
    from scripts import api

    return api.frontend_out_dir()


def _frontend_index_file():
    index_file = _frontend_out_dir() / "index.html"
    if index_file.is_file():
        return index_file
    return None


def _frontend_asset_file(asset_path: str):
    root = _frontend_out_dir().resolve()
    candidate = (root / asset_path).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if candidate.is_file():
        return candidate
    return None


def _frontend_index_response():
    import json as _json

    index_file = _frontend_index_file()
    if index_file is None:
        raise HTTPException(status_code=404, detail="frontend build not found")
    html = index_file.read_text(encoding="utf-8")
    session_token = os.environ.get("VBINVEST_LOCAL_SESSION_TOKEN", "")
    if session_token:
        script = f"<script>window.__VBINVEST_LOCAL_SESSION_TOKEN__={_json.dumps(session_token)};</script>"
        html = html.replace("</head>", f"{script}</head>", 1) if "</head>" in html else f"{script}{html}"
    return HTMLResponse(html)


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "vbinvest",
        "version": VERSION_METADATA.version,
        "build_version": VERSION_METADATA.build_version,
    }


@router.get("/", response_class=HTMLResponse)
def frontend_root():
    return _frontend_index_response()


@router.get("/_next/{asset_path:path}")
def frontend_next_asset(asset_path: str):
    asset_file = _frontend_asset_file(f"_next/{asset_path}")
    if asset_file is None:
        raise HTTPException(status_code=404, detail="frontend asset not found")
    return FileResponse(asset_file)


@router.post("/api/system/shutdown")
def system_shutdown(user=Depends(current_user)):
    from scripts import api  # late import to avoid circular dependency

    if os.environ.get("VBINVEST_LOCAL_SHUTDOWN_ENABLED") != "1" or api.LOCAL_SHUTDOWN_CALLBACK is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="local launcher shutdown is not available"
        )
    api.LOCAL_SHUTDOWN_CALLBACK()
    return {"status": "shutting_down"}


@router.post("/api/system/shutdown-beacon")
def system_shutdown_beacon(payload: ShutdownBeaconPayload):
    from scripts import api  # late import to avoid circular dependency

    if os.environ.get("VBINVEST_LOCAL_SHUTDOWN_ENABLED") != "1" or api.LOCAL_SHUTDOWN_CALLBACK is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="local launcher shutdown is not available"
        )
    if not payload.token or payload.token != os.environ.get("VBINVEST_LOCAL_SESSION_TOKEN", ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid local session token")
    api.LOCAL_SHUTDOWN_CALLBACK()
    return {"status": "shutting_down"}


@router.get("/dashboard/{slug}", response_class=HTMLResponse)
def dashboard_html(slug: str, days: int = 1260):
    items = db().fetch_dashboard_items(slug, days=days)
    if not items:
        raise HTTPException(status_code=404, detail="dashboard data not found")
    return render_dashboard_html(items, title=f"VBinvest {slug}")


@router.get("/{asset_path:path}")
def frontend_asset_or_route(asset_path: str):
    if asset_path.startswith("api/") or asset_path == "health" or asset_path.startswith("dashboard/"):
        raise HTTPException(status_code=404, detail="not found")
    asset_file = _frontend_asset_file(asset_path)
    if asset_file is not None:
        return FileResponse(asset_file)
    return _frontend_index_response()
