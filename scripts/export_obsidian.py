from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.db import DatabaseConfig, VBinvestDB
from scripts.lib.obsidian import export_research_rows


DEFAULT_VAULT = "/Volumes/nv6000t/ObsidianVault/옵시디언"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export VBinvest on-demand research to Obsidian")
    parser.add_argument("--watchlist", default="semiconductor-core")
    parser.add_argument("--date", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--vault", default=DEFAULT_VAULT)
    parser.add_argument("--input", default="reports/research/on-demand-research.json")
    return parser.parse_args()


def load_rows(path: Path, report_date: str, limit: int) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    filtered = [row for row in rows if str(row.get("report_date")) == report_date]
    if not filtered:
        filtered = rows
    return filtered[:limit] if limit else filtered


def main() -> int:
    args = parse_args()
    rows = load_rows(Path(args.input), args.date, args.limit)
    db = _connect_db_if_available()
    results = export_research_rows(rows, args.vault, db=db)
    ok_count = sum(1 for result in results if result["status"] == "ok")
    skipped_count = sum(1 for result in results if result["status"] == "skipped")
    print("VBinvest Obsidian export")
    print(f"status=ok watchlist={args.watchlist} rows={len(rows)} ok={ok_count} skipped={skipped_count}")
    for result in results:
        print(f"{result['status']} path={result['path']}")
    return 0 if skipped_count == 0 else 1


def _connect_db_if_available():
    config = DatabaseConfig.from_env(os.environ)
    db = VBinvestDB(config)
    try:
        with db.connect():
            return db
    except db._psycopg.Error:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
