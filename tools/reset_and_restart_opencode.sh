#!/usr/bin/env bash
##
# Idempotent script to reset and restart the OpenCode web server inside tmux session 'a'.
#
# Usage:
#   ./tools/reset_and_restart_opencode.sh [--yes] [--backup-dir DIR]
#
# By default the script runs in DRY-RUN mode and will only print actions. Pass --yes to perform actions.
#
# Behaviour:
#   - Ensures tmux session 'a' exists (creates if missing)
#   - Checks for a running OpenCode process inside the session and sends SIGTERM, waits, then SIGKILL if needed
#   - Optionally backs up OpenCode state files (default: ~/.config/opencode) to a timestamped directory
#   - Starts the OpenCode web server inside tmux session 'a', loading environment from repo .env if present
#   - Writes logs to state/logs/opencode_web.stdout.log and .stderr.log
#
# Safety:
#   - Default: dry-run (no destructive actions)
#   - Requires explicit --yes to actually stop/start services or remove files
#   - Does not perform git operations or remote pushes
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
TMUX_SESSION="a"
# Default start command for OpenCode web — bind to 0.0.0.0:6868 as requested by user
# Use npx opencode web if available; detection below may override with project start script
OPENCODE_CMD="npx opencode web --hostname 0.0.0.0 --port 6868"
DRY_RUN=true
BACKUP_DIR=""
LOG_DIR="$HOME/state/logs"
ENV_FILE="$REPO_ROOT/.env"

show_help() {
  sed -n '1,140p' "$0" | sed -n '1,120p'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) DRY_RUN=false; shift ;;
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown arg: $1"; show_help; exit 1 ;;
  esac
done

info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
err() { echo "[ERROR] $*" 1>&2; }

mkdir -p "$LOG_DIR"

# Detect opencode start command heuristically (project may vary)
detect_start_command() {
  # If package.json exists in repo root and a start script is defined, use it
  if [[ -f "$REPO_ROOT/package.json" ]]; then
    if grep -q '"start"' "$REPO_ROOT/package.json"; then
      # If a start script exists, prefer npm start but append hostname/port if the CLI supports it
      OPENCODE_CMD="npm run start --prefix $REPO_ROOT -- --hostname 0.0.0.0 --port 6868"
      return
    fi
  fi
  # Fallback: prefer npx opencode web with explicit host/port
  OPENCODE_CMD="npx opencode web --hostname 0.0.0.0 --port 6868"
}

detect_start_command

echo "Dry run: $DRY_RUN"
echo "Tmux session: $TMUX_SESSION"
echo "Log dir: $LOG_DIR"

if $DRY_RUN; then
  info "Running in DRY-RUN mode. No destructive actions will be performed. Use --yes to execute."
fi

# Ensure tmux is available
if ! command -v tmux >/dev/null 2>&1; then
  err "tmux not found. Please install tmux to use this script."
  exit 2
fi

# Create tmux session if missing
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
  if $DRY_RUN; then
    info "Would create tmux session '$TMUX_SESSION'"
  else
    info "Creating tmux session '$TMUX_SESSION'"
    tmux new-session -d -s "$TMUX_SESSION"
  fi
else
  info "Tmux session '$TMUX_SESSION' already exists"
fi

# Helper: find opencode web pid inside tmux session by listing pids attached to session
find_opencode_pid_in_tmux() {
  # List pids for processes whose TTY is attached to tmux panes in the session
  tmux list-panes -t "$TMUX_SESSION" -F '#{pane_pid}' 2>/dev/null || true
}

PANE_PIDS=$(find_opencode_pid_in_tmux || true)
if [[ -z "$PANE_PIDS" ]]; then
  info "No panes/pids found in tmux session '$TMUX_SESSION'"
else
  info "Panes pids: $PANE_PIDS"
fi

# Function to stop opencode in session
stop_opencode() {
  info "Attempting to stop OpenCode web inside tmux session '$TMUX_SESSION'"

  # Try to gracefully terminate any long-running processes in panes by sending C-c
  if $DRY_RUN; then
    info "Would send C-c to tmux session '$TMUX_SESSION' panes to stop processes"
    return 0
  fi

  # Send Ctrl-C to each pane
  tmux list-panes -t "$TMUX_SESSION" -F '#{pane_id}' | while read -r pane; do
    tmux send-keys -t "$pane" C-c
    sleep 1
  done

  # Wait a few seconds for processes to exit
  sleep 3

  # Check pids again; if still running, kill
  PIDS="$(find_opencode_pid_in_tmux || true)"
  if [[ -n "$PIDS" ]]; then
    info "Pids still present after SIGINT: $PIDS. Sending SIGTERM."
    for pid in $PIDS; do
      if kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" || true
      fi
    done
    sleep 2
  fi

  # Final cleanup: SIGKILL any remaining
  PIDS="$(find_opencode_pid_in_tmux || true)"
  if [[ -n "$PIDS" ]]; then
    info "Pids still present after SIGTERM: $PIDS. Sending SIGKILL."
    for pid in $PIDS; do
      if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" || true
      fi
    done
  fi

  info "Stop sequence complete"
}

# Backup opencode state if requested
backup_state() {
  local target="$1"
  if [[ -z "$target" ]]; then
    warn "No backup target provided"
    return 0
  fi
  if $DRY_RUN; then
    info "Would copy '$target' to backup directory"
    return 0
  fi
  mkdir -p "$BACKUP_DIR"
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  dest="$BACKUP_DIR/opencode_backup_$ts"
  info "Backing up $target -> $dest"
  cp -a "$target" "$dest"
}

# Start opencode web inside tmux session
start_opencode() {
  info "Starting OpenCode web inside tmux session '$TMUX_SESSION'"

  if $DRY_RUN; then
    info "Would run in tmux: $OPENCODE_CMD"
    return 0
  fi

  # Build command: source env file if exists
  if [[ -f "$ENV_FILE" ]]; then
    # Build a safe bash -lc command string. Use double-quotes for the outer string and single-quotes
    # inside the command so paths with spaces are preserved.
    CMD="bash -lc \"set -a && source '$ENV_FILE' && $OPENCODE_CMD >> '$LOG_DIR/opencode_web.stdout.log' 2>> '$LOG_DIR/opencode_web.stderr.log'\""
  else
    CMD="bash -lc \"$OPENCODE_CMD >> '$LOG_DIR/opencode_web.stdout.log' 2>> '$LOG_DIR/opencode_web.stderr.log'\""
  fi

  # Create a new window for the web process
  tmux new-window -t "$TMUX_SESSION" -n opencode_web "$CMD"
  info "Started OpenCode web in tmux window 'opencode_web' (session $TMUX_SESSION). Logs: $LOG_DIR/opencode_web.stdout.log"
}

# Main flow
if [[ -n "$BACKUP_DIR" ]]; then
  if [[ ! -d "$BACKUP_DIR" ]]; then
    if $DRY_RUN; then
      info "Would create backup dir: $BACKUP_DIR"
    else
      mkdir -p "$BACKUP_DIR"
    fi
  fi
  # backup ~/.config/opencode by default
  backup_state "$HOME/.config/opencode"
fi

stop_opencode

# Optionally check model host availability before starting
MODEL_HOST_URL="http://127.0.0.1:8000/v1/models"
if $DRY_RUN; then
  info "Would check model host at $MODEL_HOST_URL"
else
  if command -v curl >/dev/null 2>&1; then
    if ! curl -sSf "$MODEL_HOST_URL" >/dev/null 2>&1; then
      warn "Model host not reachable at $MODEL_HOST_URL. OpenCode will start but may fail to connect to model."
    else
      info "Model host reachable"
    fi
  else
    warn "curl not installed; skipping model host reachability check"
  fi
fi

start_opencode

info "Reset and restart script finished (dry-run=$DRY_RUN)"
