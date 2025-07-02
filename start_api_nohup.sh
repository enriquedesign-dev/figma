#!/usr/bin/env bash

# Figma Text API – Background server manager using nohup
# -----------------------------------------------------
# Usage:
#   ./start_api_nohup.sh start     # start server in background
#   ./start_api_nohup.sh stop      # stop server
#   ./start_api_nohup.sh status    # show running status
#   ./start_api_nohup.sh restart   # restart server
#
# The script wraps run_server.sh in nohup, writes logs to figma_api.out and
# stores the process ID in figma_api.pid to make status/stop operations easy.

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/figma_api.pid"
LOG_FILE="$BASE_DIR/figma_api.out"

start_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
    echo "✅ Figma Text API is already running (PID $(cat "$PID_FILE"))."
    exit 0
  fi

  echo "🚀 Starting Figma Text API in background…"
  cd "$BASE_DIR"
  # Run run_server.sh through nohup so it survives the session
  nohup bash "$BASE_DIR/run_server.sh" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "✅ Started with PID $! (logs: $LOG_FILE)"
}

stop_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
    PID=$(cat "$PID_FILE")
    echo "🛑 Stopping Figma Text API (PID $PID)…"
    kill "$PID"
    rm -f "$PID_FILE"
    echo "✅ Stopped."
  else
    echo "ℹ️  No running server found."
  fi
}

status_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
    echo "✅ Figma Text API is running (PID $(cat "$PID_FILE")). Log: $LOG_FILE"
  else
    echo "❌ Figma Text API is not running."
  fi
}

case "${1:-}" in
  start)   start_server ;;
  stop)    stop_server ;;
  status)  status_server ;;
  restart) stop_server; start_server ;;
  *) echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
 esac 