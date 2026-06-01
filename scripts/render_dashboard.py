from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.dashboard import render_dashboard_html
from scripts.lib.db import DatabaseConfig, VBinvestDB
from scripts.lib.indicators import add_indicators
from scripts.lib.prices import synthetic_history
from scripts.lib.watchlists import SEMICONDUCTOR_CORE


def parse_args():
    parser = argparse.ArgumentParser(description="Render VBinvest dashboard")
    parser.add_argument("--watchlist", default="semiconductor-core")
    parser.add_argument("--output", default="reports/semiconductor/latest.html")
    parser.add_argument("--mirror-output", default=None)
    parser.add_argument("--sample", action="store_true", help="render from deterministic sample data")
    parser.add_argument("--days", type=int, default=260)
    return parser.parse_args()


def sample_items(watchlist: str) -> list[dict]:
    if watchlist != "semiconductor-core":
        raise ValueError("only semiconductor-core sample rendering is implemented")
    items = []
    for asset in SEMICONDUCTOR_CORE:
        frame = add_indicators(synthetic_history(asset["symbol"]))
        items.append({"asset": asset, "history": frame})
    return items


def db_items(watchlist: str, days: int) -> tuple[list[dict], VBinvestDB]:
    config = DatabaseConfig.from_env(os.environ)
    db = VBinvestDB(config)
    items = db.fetch_dashboard_items(watchlist, days=days)
    if not items:
        raise RuntimeError(f"no DB dashboard data for watchlist={watchlist}; run startup_market_refresh.py first")
    return items, db


def write_outputs(html: str, output: Path, mirror: str | None) -> list[Path]:
    written = []
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    written.append(output)
    if mirror:
        mirror_path = Path(mirror)
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if mirror_path.resolve() != output.resolve():
            mirror_path.write_text(html, encoding="utf-8")
            written.append(mirror_path)
        snapshot = mirror_path.parent / f"daily-{__import__('datetime').date.today().isoformat()}-semiconductor-prices.html"
        snapshot.write_text(html, encoding="utf-8")
        written.append(snapshot)
    return written


def main() -> int:
    args = parse_args()
    db = None
    if args.sample:
        items = sample_items(args.watchlist)
    else:
        items, db = db_items(args.watchlist, args.days)
    html = render_dashboard_html(items)
    written = write_outputs(html, Path(args.output), args.mirror_output)
    run_id = None
    if db is not None:
        run_id = db.record_report_run(
            run_type="dashboard-refresh",
            status="ok",
            scope_slug=args.watchlist,
            failed_assets=[],
            output_summary=f"assets={len(items)} bytes={written[0].stat().st_size}",
            output_path=str(written[0]),
        )
    print(f"rendered={written[0]} assets={len(items)} bytes={written[0].stat().st_size}")
    if len(written) > 1:
        print("mirrors=" + ",".join(str(p) for p in written[1:]))
    if run_id:
        print(f"report_run={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
