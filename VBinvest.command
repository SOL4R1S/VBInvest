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

load_docker_postgres_env() {
  if [[ -n "${POSTGRES_PASSWORD:-}${VBINVEST_DB_PASSWORD:-}" ]]; then
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx 'vbinvest-postgres'; then
    return
  fi

  export VBINVEST_DB_HOST="${VBINVEST_DB_HOST:-127.0.0.1}"
  local db_name db_user db_password
  db_name="$(docker exec vbinvest-postgres printenv POSTGRES_DB 2>/dev/null || true)"
  db_user="$(docker exec vbinvest-postgres printenv POSTGRES_USER 2>/dev/null || true)"
  db_password="$(docker exec vbinvest-postgres printenv POSTGRES_PASSWORD 2>/dev/null || true)"
  [[ -n "$db_name" && -z "${POSTGRES_DB:-}" ]] && export POSTGRES_DB="$db_name"
  [[ -n "$db_user" && -z "${POSTGRES_USER:-}" ]] && export POSTGRES_USER="$db_user"
  [[ -n "$db_password" ]] && export POSTGRES_PASSWORD="$db_password"
}

load_docker_postgres_env

find_free_port() {
  "$PYTHON_BIN" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

API_PORT="$(find_free_port)"
export VBINVEST_API_BASE_URL="http://127.0.0.1:${API_PORT}"

"$PYTHON_BIN" -m uvicorn scripts.api:app --host 127.0.0.1 --port "$API_PORT" &
API_PID="$!"

cleanup() {
  kill "$API_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

(
  sleep 3
  open "http://127.0.0.1:${API_PORT}"
) &

wait "$API_PID"
