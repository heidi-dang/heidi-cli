#!/usr/bin/env bash
# Simple watchdog to ensure OpenCode web is running in tmux session 'a'.
# SAFETY: Limits backup retention to prevent SSD flooding.
set -euo pipefail

TMUX_SESSION="a"
CHECK_INTERVAL=10
RESTART_COOLDOWN=120  # Wait at least 2 minutes between restart attempts
LOG_DIR="$HOME/state/logs"
BACKUP_DIR="$HOME/state/backups/opencode"
MAX_BACKUPS=3  # Keep only the 3 most recent backups
mkdir -p "$LOG_DIR" "$HOME/state/run"

LAST_RESTART=0

is_running() {
  ss -ltnp | grep -q ":6868 " || return 1
}

prune_old_backups() {
  if [[ -d "$BACKUP_DIR" ]]; then
    local count
    count=$(ls -1d "$BACKUP_DIR"/opencode_backup_* 2>/dev/null | wc -l)
    if (( count > MAX_BACKUPS )); then
      local to_remove=$(( count - MAX_BACKUPS ))
      ls -1d "$BACKUP_DIR"/opencode_backup_* 2>/dev/null | head -n "$to_remove" | while read -r dir; do
        echo "[watchdog] Pruning old backup: $dir" >> "$LOG_DIR/opencode_watchdog.log"
        rm -rf "$dir"
      done
    fi
  fi
}

start_opencode() {
  local now
  now=$(date +%s)
  local elapsed=$(( now - LAST_RESTART ))
  
  if (( elapsed < RESTART_COOLDOWN )); then
    echo "[watchdog] Cooldown active (${elapsed}s < ${RESTART_COOLDOWN}s), skipping restart" >> "$LOG_DIR/opencode_watchdog.log"
    return
  fi
  
  LAST_RESTART=$now
  echo "[watchdog] Starting OpenCode web..." >> "$LOG_DIR/opencode_watchdog.log"
  
  # Prune old backups BEFORE creating a new one
  prune_old_backups
  
  # Use the reset script to start cleanly
  /home/heidi/work/heidi-cli/tools/reset_and_restart_opencode.sh --yes --backup-dir "$BACKUP_DIR" >> "$LOG_DIR/opencode_watchdog.log" 2>&1 || true
}

echo "[watchdog] Starting loop" >> "$LOG_DIR/opencode_watchdog.log"
while true; do
  if is_running; then
    sleep $CHECK_INTERVAL
    continue
  fi
  echo "[watchdog] opencode not running, starting" >> "$LOG_DIR/opencode_watchdog.log"
  start_opencode
  sleep $CHECK_INTERVAL
done
