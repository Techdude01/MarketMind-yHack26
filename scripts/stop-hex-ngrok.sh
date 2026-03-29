#!/usr/bin/env bash
set -euo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly NGROK_PID_FILE="${ROOT_DIR}/.ngrok-postgres.pid"

if [[ ! -f "${NGROK_PID_FILE}" ]]; then
  echo "No ngrok PID file found. Nothing to stop."
  exit 0
fi

ngrok_pid="$(cat "${NGROK_PID_FILE}")"
if kill -0 "${ngrok_pid}" >/dev/null 2>&1; then
  kill "${ngrok_pid}"
  echo "Stopped ngrok process ${ngrok_pid}."
else
  echo "Process ${ngrok_pid} is not running."
fi

rm -f "${NGROK_PID_FILE}"
