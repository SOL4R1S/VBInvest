from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


EXPECTED_ORIGIN_URL: Final = "https://github.com/SOL4R1S/VBInvest.git"


@dataclass(frozen=True, slots=True)
class HookResult:
    ok: bool
    message: str


def validate_origin_url(origin_url: str) -> HookResult:
    if origin_url.strip() == EXPECTED_ORIGIN_URL:
        return HookResult(ok=True, message="origin=ok")
    return HookResult(
        ok=False,
        message=f"origin must point to {EXPECTED_ORIGIN_URL}",
    )


def validate_branch_name(branch_name: str) -> HookResult:
    branch = branch_name.strip()
    allowed_prefixes = ("feature/", "release/", "hotfix/")
    if branch in {"main", "develop"} or branch.startswith(allowed_prefixes):
        return HookResult(ok=True, message="branch=ok")
    return HookResult(ok=False, message="branch must follow the VBinvest Git Flow policy")


def current_origin_url(project_root: Path) -> str:
    completed = subprocess.run(
        ("git", "remote", "get-url", "origin"),
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def current_branch_name(project_root: Path) -> str:
    completed = subprocess.run(
        ("git", "branch", "--show-current"),
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def run_secret_scan(project_root: Path) -> HookResult:
    completed = subprocess.run(
        ("./.venv/bin/python", "scripts/secret_scan.py"),
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode == 0:
        return HookResult(ok=True, message="secret_scan=ok")
    output = completed.stdout.strip() or completed.stderr.strip() or "secret scan failed"
    return HookResult(ok=False, message=output)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    project_root = Path(args[0]).resolve() if args else Path.cwd()
    checks = [
        validate_origin_url(current_origin_url(project_root)),
        validate_branch_name(current_branch_name(project_root)),
        run_secret_scan(project_root),
    ]
    failed = [check for check in checks if not check.ok]
    if failed:
        print("\n".join(check.message for check in failed), file=sys.stderr)
        return 1
    print("\n".join(check.message for check in checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
