from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any


GENERATED_MARKER = "<!-- VBinvest:generated -->"


class ManualNoteError(RuntimeError):
    pass


def note_path(vault: str | Path, symbol: str, report_date: date | str) -> Path:
    date_text = report_date.isoformat() if isinstance(report_date, date) else str(report_date)
    safe_symbol = sanitize_symbol(symbol)
    return Path(vault) / "30 Projects" / "VBinvest" / safe_symbol / f"{date_text}.md"


def sanitize_symbol(symbol: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", symbol).strip("-")
    if not sanitized:
        raise ValueError("empty ticker symbol")
    return sanitized


def render_note(row: dict[str, Any]) -> str:
    symbol = row["target_slug"]
    report_date = _date_text(row["report_date"])
    risks = _json_list(row.get("risks"))
    triggers = _json_list(row.get("triggers"))
    sources = _json_list(row.get("sources"))
    metrics = _json_dict(row.get("metrics_snapshot"))
    target = _json_dict(row.get("target_price_summary"))
    lines = [
        "---",
        f"ticker: {symbol}",
        f"report_date: {report_date}",
        f"opinion: {row.get('opinion')}",
        "project: VBinvest",
        "---",
        "",
        GENERATED_MARKER,
        "",
        f"# {symbol} On-Demand Research",
        "",
        "Backlink: [[VBinvest]]",
        "",
        f"Opinion: **{row.get('opinion')}**",
        "",
        *_snapshot_lines(metrics, target),
        "## Thesis",
        str(row.get("thesis") or ""),
        "",
        "## Bull / Base / Bear",
        f"- Bull: {row.get('bull') or ''}",
        f"- Base: {row.get('base') or ''}",
        f"- Bear: {row.get('bear') or ''}",
        "",
        "## Risks",
        *[f"- {item}" for item in risks],
        "",
        "## Triggers",
        *[f"- {item}" for item in triggers],
        "",
        "## Sources",
        *_source_lines(sources),
        "",
        f"DB run ID: {row.get('run_id') or row.get('ai_run_id') or 'n/a'}",
        "",
        "Disclaimer: research/learning only, not investment advice.",
        "",
    ]
    return "\n".join(lines)


def write_generated_note(path: Path, markdown: str) -> None:
    if path.exists() and GENERATED_MARKER not in path.read_text(encoding="utf-8"):
        raise ManualNoteError(f"manual note without generated marker: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def export_research_rows(rows: list[dict[str, Any]], vault: str | Path, *, db=None) -> list[dict[str, str]]:
    results = []
    vault_path = Path(vault)
    for row in rows:
        path = note_path(vault_path, row["target_slug"], row["report_date"])
        markdown = render_note(row)
        try:
            write_generated_note(path, markdown)
            status = "ok"
            error_message = None
        except ManualNoteError as exc:
            status = "skipped"
            error_message = str(exc)
        relative_path = str(path.relative_to(vault_path))
        file_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        if db is not None:
            db.record_obsidian_export(
                export_id=str(uuid.uuid4()),
                view_id=row.get("view_id"),
                target_slug=row["target_slug"],
                report_date=_date_text(row["report_date"]),
                vault_path=str(vault_path),
                relative_path=relative_path,
                file_path=str(path),
                file_hash=file_hash,
                status=status,
                error_message=error_message,
            )
        results.append({"status": status, "path": str(path), "error": error_message or ""})
    return results


def _source_lines(sources: list[Any]) -> list[str]:
    if not sources:
        return ["- source_gap"]
    lines = []
    for source in sources:
        if not isinstance(source, dict):
            lines.append(f"- {source}")
            continue
        title = source.get("title") or source.get("kind") or "source"
        url = source.get("url")
        lines.append(f"- [{title}]({url})" if url else f"- {title}")
    return lines


def _snapshot_lines(metrics: dict[str, Any], target: dict[str, Any]) -> list[str]:
    if not metrics and not target:
        return []
    currency = _text(target.get("currency")) or _text(metrics.get("currency"))
    lines = [
        "## Price / Target Snapshot",
        f"- Current price: {_number(metrics.get('current_price'))}{_currency_suffix(currency)} ({_text(metrics.get('date')) or 'date n/a'})",
        f"- Target price: {_target_price_text(target, currency)}",
        f"- Implied upside: {_percent(target.get('implied_upside'))}",
        (
            f"- Returns: 1D {_percent(metrics.get('return_1d'))} · "
            f"1W {_percent(metrics.get('return_1w'))} · "
            f"1M {_percent(metrics.get('return_1m'))} · "
            f"3M {_percent(metrics.get('return_3m'))}"
        ),
        (
            f"- Technicals: RSI14: {_number(metrics.get('rsi14'), decimals=1)} · "
            f"MA5/20/50/120 {_number(metrics.get('ma5'))} / {_number(metrics.get('ma20'))} / "
            f"{_number(metrics.get('ma50'))} / {_number(metrics.get('ma120'))}"
        ),
        f"- 52W: high {_number(metrics.get('high_52w'))} · drawdown {_percent(metrics.get('drawdown_52w'))}",
        f"- Target source: {_text(target.get('source_title')) or _text(target.get('message')) or 'n/a'}",
        "",
    ]
    return lines


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    return value if isinstance(value, list) else []


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, str) and value.strip():
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    return value if isinstance(value, dict) else {}


def _target_price_text(target: dict[str, Any], currency: str) -> str:
    if target.get("status") not in {"found", "estimated"}:
        return _text(target.get("message")) or "not found in collected sources"
    return f"{_number(target.get('target_price'))}{_currency_suffix(currency)}"


def _number(value: Any, *, decimals: int = 2) -> str:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return "n/a"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"


def _percent(value: Any) -> str:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return "n/a"
    return f"{value * 100:+.1f}%"


def _currency_suffix(currency: str) -> str:
    return f" {currency}" if currency else ""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _date_text(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)
