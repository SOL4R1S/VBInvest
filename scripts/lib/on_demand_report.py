from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from scripts.lib.ai_provider import AIProviderConfigError, AIProviderError, build_research_ai_client_from_env
from scripts.lib.config import ConfigError, ProviderSettings, load_local_config
from scripts.lib.obsidian import ManualNoteError, note_path, render_note, write_generated_note
from scripts.lib.research import GuardrailError, build_on_demand_research_view, build_source_packet


class OnDemandReportError(RuntimeError):
    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


@dataclass(frozen=True, slots=True)
class OnDemandReportPaths:
    obsidian_path: str | None
    report_path: str | None
    report_url: str | None


class OnDemandReportStore(Protocol):
    def fetch_profile_by_auth_user(self, auth_user_id: str) -> dict[str, Any] | None:
        ...

    def fetch_asset_dashboard_item(self, symbol: str, *, days: int = 1260) -> dict[str, Any] | None:
        ...

    def upsert_research_views(self, rows: list[dict[str, Any]]) -> int:
        ...

    def record_report_run(self, **kwargs: object) -> str:
        ...


def generate_on_demand_research_for_asset(
    store: OnDemandReportStore,
    auth_user_id: str,
    symbol: str,
    *,
    obsidian_vault_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if store.fetch_profile_by_auth_user(auth_user_id) is None:
        raise LookupError("authenticated profile not found")
    item = store.fetch_asset_dashboard_item(symbol)
    if item is None:
        raise LookupError("asset data not found")

    try:
        row = _build_research_row(item, environ or os.environ)
        paths = _write_obsidian(row, obsidian_vault_path)
        store.upsert_research_views([row])
        run_id = store.record_report_run(
            run_type="on-demand-research",
            status="ok",
            scope_type="asset",
            scope_slug=symbol,
            failed_assets=[],
            output_summary=f"research=1 opinion={row['opinion']}",
            output_path=paths.obsidian_path,
            error_message=None,
        )
    except (AIProviderConfigError, AIProviderError, GuardrailError) as exc:
        raise _record_failure(store, symbol, _safe_ai_error_message(exc)) from exc
    except ManualNoteError as exc:
        raise _record_failure(store, symbol, "Obsidian export failed") from exc

    result = dict(row)
    result["run_id"] = run_id
    result["obsidian_path"] = paths.obsidian_path
    result["report_path"] = paths.report_path
    result["report_url"] = paths.report_url
    return result


def _build_research_row(item: dict[str, Any], environ: Mapping[str, str]) -> dict[str, Any]:
    history = item["history"]
    latest = history.iloc[-1].to_dict()
    packet = build_source_packet(item["asset"], latest, news=item.get("news", []), disclosures=item.get("disclosures", []))
    ai_client = build_research_ai_client_from_env(_ai_environ(environ))
    return build_on_demand_research_view(
        item["asset"],
        latest,
        packet,
        ai_credentials_present=ai_client is not None,
        model_provider=ai_client.provider_name if ai_client is not None else None,
        ai_client=ai_client,
    )


def _write_obsidian(row: dict[str, Any], vault_path: str | Path | None) -> OnDemandReportPaths:
    if vault_path is None:
        return OnDemandReportPaths(obsidian_path=None, report_path=None, report_url=None)
    path = note_path(vault_path, row["target_slug"], row["report_date"])
    write_generated_note(path, render_note(row))
    return OnDemandReportPaths(obsidian_path=str(path), report_path=str(path), report_url=None)


def _ai_environ(environ: Mapping[str, str]) -> dict[str, str]:
    merged = dict(environ)
    if "VBINVEST_CONFIG_PATH" not in environ:
        return merged
    try:
        config = load_local_config(environ=environ)
    except ConfigError as exc:
        raise AIProviderConfigError(str(exc)) from exc
    _merge_provider_settings(merged, config.providers)
    return merged


def _merge_provider_settings(environ: dict[str, str], providers: ProviderSettings) -> None:
    if providers.ai_provider_name and not environ.get("AI_PROVIDER_NAME"):
        environ["AI_PROVIDER_NAME"] = providers.ai_provider_name
    if providers.ai_base_url and not environ.get("AI_PROVIDER_BASE_URL"):
        environ["AI_PROVIDER_BASE_URL"] = providers.ai_base_url
    if providers.ai_model and not environ.get("AI_PROVIDER_MODEL"):
        environ["AI_PROVIDER_MODEL"] = providers.ai_model
    if providers.ai_api_key and not _has_ai_api_key(environ):
        environ["AI_API_KEY"] = providers.ai_api_key


def _has_ai_api_key(environ: Mapping[str, str]) -> bool:
    return any(environ.get(key, "").strip() for key in ("AI_API_KEY", "AI_PROVIDER_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"))


def _safe_ai_error_message(exc: AIProviderConfigError | AIProviderError | GuardrailError) -> str:
    message = str(exc).strip()
    return message or "AI report generation failed"


def _record_failure(
    store: OnDemandReportStore,
    symbol: str,
    user_message: str,
) -> OnDemandReportError:
    store.record_report_run(
        run_type="on-demand-research",
        status="failed",
        scope_type="asset",
        scope_slug=symbol,
        failed_assets=[symbol],
        output_summary="research=0",
        output_path=None,
        error_message=user_message,
    )
    return OnDemandReportError(user_message)
