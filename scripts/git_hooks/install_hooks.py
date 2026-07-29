from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import Final


HOOKS: Final = {
    "commit-msg": "./.venv/bin/python scripts/git_hooks/check_commit_msg.py \"$1\"",
    "pre-commit": "git diff --cached --name-only --diff-filter=ACMRT | ./.venv/bin/python scripts/git_hooks/check_paths.py && git diff --cached --name-only --diff-filter=ACMRT | xargs -r ./.venv/bin/python scripts/secret_scan.py",
    "pre-push": "./.venv/bin/python scripts/git_hooks/check_pre_push.py",
}


def install_hooks(project_root: Path) -> list[Path]:
    hooks_dir = project_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for hook_name, command in HOOKS.items():
        hook_path = hooks_dir / hook_name
        hook_path.write_text(_hook_body(project_root, command), encoding="utf-8")
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)
        installed.append(hook_path)
    return installed


def _hook_body(project_root: Path, command: str) -> str:
    return "\n".join(
        [
            "#!/bin/sh",
            "set -eu",
            'PROJECT_ROOT="$(git rev-parse --show-toplevel)"',
            'cd "$PROJECT_ROOT"',
            'export PATH="$PROJECT_ROOT/.venv/bin:$PATH"',
            command,
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    project_root = Path(args[0]).resolve() if args else Path.cwd()
    installed = install_hooks(project_root)
    for hook_path in installed:
        print(f"installed {os.fspath(hook_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
