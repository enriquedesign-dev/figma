#!/usr/bin/env bash

# =========================================================================
#  Figma Text API – One-stop service manager
# -------------------------------------------------------------------------
#  Usage:
#     ./manage_api.sh start      # start server in background (nohup)
#     ./manage_api.sh stop       # stop server
#     ./manage_api.sh restart    # restart server
#     ./manage_api.sh status     # show status
#     ./manage_api.sh logs       # tail logs (Ctrl-C to exit)
#
#  The script stores the PID in manage_api.pid and writes logs to logs/figma_api.log.
#  It survives SSH session termination thanks to `nohup` (no need for tmux/screen).
# =========================================================================

set -euo pipefail

# -----------------------------  Styling helpers  -------------------------
RED="\e[31m"; GREEN="\e[32m"; YELLOW="\e[33m"; BLUE="\e[34m"; RESET="\e[0m"
info()    { echo -e "${BLUE}ℹ️  $*${RESET}"; }
success() { echo -e "${GREEN}✅ $*${RESET}"; }
warning() { echo -e "${YELLOW}⚠️  $*${RESET}"; }
error()   { echo -e "${RED}❌ $*${RESET}"; }

# -----------------------------  Paths  -----------------------------------
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/figma_api.log"
PID_FILE="$BASE_DIR/manage_api.pid"
ENV_DIR="$BASE_DIR/venv"

mkdir -p "$LOG_DIR"

# -----------------------------  Functions  -------------------------------

start_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    success "Figma Text API already running (PID $(cat "$PID_FILE"))."
    exit 0
  fi

  # Ensure venv exists
  if [[ ! -d "$ENV_DIR" ]]; then
    warning "Virtualenv not found – creating one and installing dependencies…"
    python3 -m venv "$ENV_DIR"
    source "$ENV_DIR/bin/activate"
    pip install -r requirements.txt
  else
    source "$ENV_DIR/bin/activate"
  fi

  # Ensure DB tables exist
  python - <<'PY'
import asyncio, database; asyncio.run(database.create_tables())
PY

  info "Launching API… (logs: $LOG_FILE)"
  nohup python main.py >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  success "Started Figma Text API (PID $!)."
}

stop_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    PID=$(cat "$PID_FILE")
    info "Stopping Figma Text API (PID $PID)…"
    kill "$PID" && rm -f "$PID_FILE"
    success "Stopped."
  else
    warning "Server is not running."
  fi
}

status_server() {
  if [[ -f "$PID_FILE" ]] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    success "Figma Text API running (PID $(cat "$PID_FILE")). Log: $LOG_FILE"
  else
    warning "Figma Text API is not running."
  fi
}

tail_logs() {
  if [[ -f "$LOG_FILE" ]]; then
    info "Tailing logs – press Ctrl+C to exit."
    tail -f "$LOG_FILE"
  else
    warning "Log file not found yet ($LOG_FILE). Start the server first."
  fi
}

case "${1:-}" in
  start) start_server ;;
  stop) stop_server ;;
  restart) stop_server; start_server ;;
  status) status_server ;;
  logs) tail_logs ;;
  *) echo "Usage: $0 {start|stop|restart|status|logs}"; exit 1 ;;
esac 