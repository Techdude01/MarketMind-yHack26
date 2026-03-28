#!/usr/bin/env bash
set -euo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ENV_FILE="${ROOT_DIR}/.env"
readonly NGROK_PID_FILE="${ROOT_DIR}/.ngrok-postgres.pid"
readonly NGROK_LOG_FILE="${ROOT_DIR}/.ngrok-postgres.log"
readonly POSTGRES_LOCAL_PORT="5433"
readonly NGROK_API_URL="http://127.0.0.1:4040/api/tunnels"
readonly MAX_RETRIES=25
readonly RETRY_DELAY_SECONDS=1

function check_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
}

function read_env_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo ""
    return
  fi
  local value
  value="$(awk -F= -v env_key="${key}" '$1==env_key{print substr($0, index($0,$2)); exit}' "${ENV_FILE}")"
  echo "${value}"
}

function ensure_postgres_running() {
  echo "Starting postgres service with Docker Compose..."
  docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d postgres >/dev/null
}

function start_ngrok_tunnel() {
  if [[ -f "${NGROK_PID_FILE}" ]]; then
    local existing_pid
    existing_pid="$(cat "${NGROK_PID_FILE}")"
    if kill -0 "${existing_pid}" >/dev/null 2>&1; then
      echo "ngrok tunnel already running (pid ${existing_pid})."
      return
    fi
    rm -f "${NGROK_PID_FILE}"
  fi
  echo "Starting ngrok tcp tunnel on localhost:${POSTGRES_LOCAL_PORT}..."
  nohup ngrok tcp "${POSTGRES_LOCAL_PORT}" >"${NGROK_LOG_FILE}" 2>&1 &
  local ngrok_pid="$!"
  echo "${ngrok_pid}" >"${NGROK_PID_FILE}"
}

function fetch_tunnel_address() {
  local output=""
  local attempt=1
  while [[ "${attempt}" -le "${MAX_RETRIES}" ]]; do
    output="$(curl -s "${NGROK_API_URL}" | python3 -c '
import json
import sys
try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)
for tunnel in payload.get("tunnels", []):
    public_url = str(tunnel.get("public_url", ""))
    if public_url.startswith("tcp://"):
        print(public_url)
        sys.exit(0)
print("")
')"
    if [[ -n "${output}" ]]; then
      echo "${output}"
      return
    fi
    sleep "${RETRY_DELAY_SECONDS}"
    attempt=$((attempt + 1))
  done
  echo ""
}

function print_hex_connection_details() {
  local tunnel_url="$1"
  local tunnel_host="${tunnel_url#tcp://}"
  local host="${tunnel_host%:*}"
  local port="${tunnel_host##*:}"
  local database_name
  local username
  local password
  database_name="$(read_env_value "POSTGRES_DB")"
  username="$(read_env_value "POSTGRES_USER")"
  password="$(read_env_value "POSTGRES_PASSWORD")"
  if [[ -z "${database_name}" ]]; then
    database_name="postgres"
  fi
  echo
  echo "Use these values in Hex:"
  echo "Name:      Local Docker Postgres"
  echo "Host:      ${host}"
  echo "Port:      ${port}"
  echo "Database:  ${database_name}"
  echo "Username:  ${username}"
  echo "Password:  ${password}"
  echo
  echo "Tunnel process info:"
  echo "PID file:  ${NGROK_PID_FILE}"
  echo "Log file:  ${NGROK_LOG_FILE}"
  echo
  echo "When done, stop with: ./scripts/stop-hex-ngrok.sh"
}

check_command "docker"
check_command "ngrok"
check_command "curl"
check_command "python3"

ensure_postgres_running
start_ngrok_tunnel

tunnel_url="$(fetch_tunnel_address)"
if [[ -z "${tunnel_url}" ]]; then
  if awk '/ERR_NGROK_8013/ {found=1} END {exit !found}' "${NGROK_LOG_FILE}" >/dev/null 2>&1; then
    echo "ngrok TCP tunnel requires account verification (card on file)." >&2
    echo "Add verification at https://dashboard.ngrok.com/settings#id-verification and retry." >&2
  fi
  echo "Failed to discover ngrok tunnel address. Check ${NGROK_LOG_FILE}." >&2
  exit 1
fi

print_hex_connection_details "${tunnel_url}"
