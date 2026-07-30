"""Settings, providers, and user profile routes."""

from __future__ import annotations

import os
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from scripts.lib.ai_catalog import provider_catalog
from scripts.lib.ai_cli import detect_ai_cli
from scripts.lib.config import (
    ConfigError,
    config_path_from_env,
    load_local_config,
    parse_report_run_summary,
    provider_status,
    write_local_config,
)
from scripts.routers.deps import (
    FirstRunSetupPayload,
    LanguageSettingsPayload,
    PostgresOperationalError,
    auth_db,
    build_first_run_config,
    current_user,
    db,
)

router = APIRouter()


@router.get("/api/settings")
def settings():
    try:
        config = load_local_config()
        latest_summary = {
            "status": None,
            "watchlist": None,
            "completed_at": None,
            "news_items": 0,
            "disclosures": 0,
            "provider_disabled": [],
        }
        try:
            latest_run = db().fetch_latest_report_run("startup-market-refresh", "semiconductor-core")
        except PostgresOperationalError:
            latest_run = None
        if latest_run is not None:
            latest_summary.update(
                {
                    "status": latest_run.get("status"),
                    "watchlist": latest_run.get("scope_slug"),
                    "completed_at": (
                        latest_run["completed_at"].isoformat()
                        if hasattr(latest_run.get("completed_at"), "isoformat")
                        else latest_run.get("completed_at")
                    ),
                }
            )
            parsed = parse_report_run_summary(latest_run.get("output_summary"))
            if isinstance(parsed, dict):
                latest_summary["news_items"] = parsed.get("news_items", 0)
                latest_summary["disclosures"] = parsed.get("disclosures", 0)
                latest_summary["provider_disabled"] = parsed.get("provider_disabled", [])
        return {
            **config.redacted(),
            "provider_status": provider_status(config, os.environ),
            "latest_startup_refresh": latest_summary,
        }
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/settings/first-run")
def save_first_run_settings(payload: FirstRunSetupPayload):
    try:
        config = build_first_run_config(payload)
        write_local_config(config, config_path_from_env(os.environ))
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=f"{exc.field}: {exc.reason}") from exc
    return {
        **config.redacted(),
        "provider_status": provider_status(config, os.environ),
    }


@router.patch("/api/settings/language")
def patch_settings_language(payload: LanguageSettingsPayload, user=Depends(current_user)):
    try:
        config = load_local_config()
        updated = replace(config, language=payload.language)
        write_local_config(updated, config_path_from_env(os.environ))
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **updated.redacted(),
        "provider_status": provider_status(updated, os.environ),
    }


@router.get("/api/providers/opendart/status")
def opendart_provider_status(check: bool = False):
    try:
        config = load_local_config()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status_payload = provider_status(config, os.environ)["opendart"]
    status_text = status_payload.get("status")
    source = status_payload.get("source")
    if status_text == "missing_key":
        return {"status": "missing_key", "source": source, "configured": False}
    if not check:
        return {"status": "enabled", "source": source, "configured": True}
    from scripts import api

    result = api.check_opendart_api_key(api.load_opendart_api_key())
    return {
        "status": result.status,
        "source": source,
        "configured": result.status == "enabled",
        "provider_code": result.provider_code,
        "message": result.message,
    }


@router.get("/api/providers/ai/status")
def ai_provider_status():
    try:
        config = load_local_config()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ai_status = provider_status(config, os.environ)["ai"]
    return {
        **ai_status,
        "catalog": [entry.as_dict() for entry in provider_catalog()],
        "cli": {
            "codex": detect_ai_cli(
                "codex",
                executable_path=os.environ.get("CODEX_CLI_PATH"),
                login_command="codex login --device-auth",
            ).as_dict(),
            "copilot": detect_ai_cli(
                "copilot",
                executable_path=os.environ.get("COPILOT_CLI_PATH"),
                login_command="copilot login",
            ).as_dict(),
        },
    }


@router.get("/api/me")
def me(user=Depends(current_user)):
    profile = auth_db().fetch_profile_by_auth_user(user.auth_user_id)
    return {"auth_user_id": user.auth_user_id, "email": user.email, "provider": "local", "profile": profile}
