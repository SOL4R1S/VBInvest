from __future__ import annotations

import re
import sys
from pathlib import Path


SECRET_ASSIGNMENT = re.compile(r"^(?P<key>[A-Z0-9_]*(?:PASSWORD|SECRET|SERVICE_ROLE|CLIENT_SECRET)[A-Z0-9_]*)=(?P<value>.+)$")
DEFAULT_PATHS = [Path("README.md"), Path("docs"), Path("postgres/.env.example"), Path("frontend/.env.example")]


def scan_text(text: str, label: str) -> list[str]:
    findings = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = SECRET_ASSIGNMENT.match(line)
        if not match:
            continue
        value = match.group("value").strip()
        key = match.group("key")
        if value.startswith("<") and value.endswith(">"):
            continue
        findings.append(f"{label}: {key} must use a <placeholder> value")
    return findings


def iter_files(paths: list[Path]):
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for child in path.rglob("*"):
            if child.is_file() and child.suffix in {".md", ".env", ".example", ".txt", ".json", ".yml", ".yaml"}:
                yield child


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    paths = [Path(item) for item in args] if args else DEFAULT_PATHS
    findings = []
    for path in iter_files(paths):
        findings.extend(scan_text(path.read_text(encoding="utf-8"), str(path)))
    if findings:
        print("\n".join(findings))
        return 1
    print("secret_scan=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
