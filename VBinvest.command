#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

save_secret() {
  local account="$1"
  local value="${(P)account:-}"
  if [[ -n "$value" ]]; then
    "$PYTHON_BIN" -m scripts.save_secret "$account"
    unset "$account"
  fi
}

save_secret "AI_API_KEY"
save_secret "OPENDART_API_KEY"

exec "$PYTHON_BIN" -m scripts.launcher "$@"
