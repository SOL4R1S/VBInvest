from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.config import ConfigError, load_opendart_api_key
from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.local_scheduler import LocalScheduler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the VBinvest local scheduler tick")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--include-news", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        store = build_database_from_local_config(environ=os.environ)
        result = LocalScheduler(store).tick(
            dry_run=args.dry_run,
            no_network=args.no_network,
            include_news=args.include_news,
            limit=args.limit,
            force=args.force,
            dart_api_key=load_opendart_api_key(environ=os.environ),
            lock_holder=f"cli:{os.getpid()}",
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"local scheduler tick failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
