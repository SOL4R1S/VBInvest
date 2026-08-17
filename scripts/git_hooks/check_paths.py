from __future__ import annotations

import sys
from pathlib import PurePosixPath


def find_forbidden_paths(paths: list[str]) -> list[str]:
    findings: list[str] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/").strip()
        if not normalized:
            continue
        reason = _forbidden_reason(PurePosixPath(normalized))
        if reason:
            findings.append(f"{normalized}: {reason}")
    return findings


def _forbidden_reason(path: PurePosixPath) -> str:
    name = path.name
    first = path.parts[0] if path.parts else ""
    if name == ".env" or (name.endswith(".env") and name != ".env.example"):
        return "local env files must not be committed"
    if name.endswith((".sqlite", ".sqlite3", ".db")):
        return "local database files must not be committed"
    if first in {"reports", "generated_reports"}:
        return "generated reports must not be committed"
    if first == "evidence":
        return "local QA evidence must not be committed"
    if first == ".omo":
        return "local orchestration state must not be committed"
    if first in {".agents", ".apm"} or path.as_posix() in {"AGENTS.md", "HERMES.md", "SOURCE_OF_TRUTH.md"}:
        return "local agent/operator context must not be committed"
    blocked_scheduled_research_paths = {
        "scripts/weekly_pipeline.py",
        "scripts/weekly_research_analysis.py",
        "frontend/app/api/cron/weekly-research/route.ts",
    }
    if path.as_posix() in blocked_scheduled_research_paths:
        return "scheduled recurring research pipeline must not be committed"
    blocked_scheduled_market_paths = {
        "scripts/daily_market_ingest.py",
        "scripts/lib/daily_scheduler.py",
        "frontend/app/api/cron/daily-ingest/route.ts",
    }
    if path.as_posix() in blocked_scheduled_market_paths:
        return "scheduled market ingest surface must not be committed"
    if first in {"vault", "ObsidianVault"} or "ObsidianVault" in path.parts:
        return "vault links or exports must not be committed"
    if first in {".vbinvest", "app-data"}:
        return "local app data must not be committed"
    return ""


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    paths = args if args else [line.strip() for line in sys.stdin if line.strip()]
    findings = find_forbidden_paths(paths)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("path_guard=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
