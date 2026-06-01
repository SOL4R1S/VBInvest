from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.validate import validate_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a VBinvest HTML report")
    parser.add_argument("path")
    args = parser.parse_args()
    result = validate_html(args.path)
    if result.ok:
        print(f"validation=ok path={args.path}")
        return 0
    print(f"validation=failed path={args.path} errors={'; '.join(result.errors)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
