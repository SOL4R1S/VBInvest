from __future__ import annotations

import os
import sys
from typing import Mapping

from scripts.lib.keychain import SecretWriteStore, platform_secret_store


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    store: SecretWriteStore | None = None,
) -> int:
    args = sys.argv[1:] if argv is None else argv
    env = os.environ if environ is None else environ
    if len(args) != 1:
        print("usage: python -m scripts.save_secret ACCOUNT", file=sys.stderr)
        return 2
    account = args[0]
    value = env.get(account, "")
    if not value:
        return 0
    secret_store = store or platform_secret_store()
    secret_store.set(account, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
