#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
TERMINAL_WINDOW_ID="$(osascript -e 'tell application "Terminal" to id of front window' 2>/dev/null || true)"

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

if [[ "${VBINVEST_FOREGROUND:-}" == "1" ]]; then
  exec "$PYTHON_BIN" -m scripts.launcher "$@"
fi

LOG_DIR="$HOME/Library/Logs/VBinvest"
mkdir -p "$LOG_DIR"
nohup "$PYTHON_BIN" -m scripts.launcher "$@" >> "$LOG_DIR/launcher.log" 2>&1 &
disown
echo "VBinvest is starting in the background. Log: $LOG_DIR/launcher.log"
if [[ "${VBINVEST_KEEP_TERMINAL:-}" != "1" ]]; then
  if [[ -n "$TERMINAL_WINDOW_ID" ]]; then
    (
      sleep 1
      osascript -e "tell application \"Terminal\" to close (first window whose id is $TERMINAL_WINDOW_ID)" >/dev/null 2>&1 || true
    ) &
    disown
  fi
fi
