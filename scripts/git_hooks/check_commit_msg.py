from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


COMMIT_PATTERN: Final = re.compile(
    r"^(feat|fix|docs|test|build|ci|chore|refactor)(\([a-z0-9._-]+\))?!?: .+"
)


@dataclass(frozen=True, slots=True)
class HookResult:
    ok: bool
    message: str


def validate_commit_message(message: str) -> HookResult:
    first_line = message.splitlines()[0].strip() if message.splitlines() else ""
    if COMMIT_PATTERN.match(first_line):
        return HookResult(ok=True, message="commit_msg=ok")
    return HookResult(
        ok=False,
        message=(
            "Commit message must follow Conventional Commit format, "
            "for example: chore: initialize git flow"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: check_commit_msg.py <commit-msg-file>", file=sys.stderr)
        return 2
    message = Path(args[0]).read_text(encoding="utf-8")
    result = validate_commit_message(message)
    output = sys.stdout if result.ok else sys.stderr
    print(result.message, file=output)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
