#!/usr/bin/env bash
set -euo pipefail

HEIDI_CMD="${HEIDI_CMD:-heidi}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

run_or_fail() {
  local label="$1"
  shift
  echo "Command: $*"
  "$@" || fail "$label (exit=$?)"
}

has_escapes() {
  # returns 0 if ESC found
  LC_ALL=C grep -q $'\x1b' || return 1
}

expect_json_only() {
  local out="$1"
  if ! echo "$out" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then
    head=$(echo "$out" | head -c 200 | tr '\n' '\\n')
    echo "Invalid JSON. First 200 chars: $head" >&2
    fail "JSON validation failed"
  fi
  if printf "%s" "$out" | has_escapes; then
    fail "JSON output contains ANSI escapes"
  fi
}

echo "=========================================="
echo "Heidi CLI Smoke (Render Policy / Plain / JSON)"
echo "=========================================="

echo ""
echo "=== Test 1: plain flag end-to-end (setup) ==="
echo "NOTE: This is interactive; answer prompts or Ctrl+C to exit."
echo "Command: $HEIDI_CMD --plain setup"
$HEIDI_CMD --plain setup || true

echo ""
echo "=== Test 2: plain flag end-to-end (doctor) ==="
run_or_fail "plain doctor" "$HEIDI_CMD" --plain doctor

echo ""
echo "=== Test 3: JSON integrity (global --json with status) ==="
OUT=$($HEIDI_CMD --json status 2>/dev/null) || fail "heidi --json status (exit=$?)"
[ -n "$OUT" ] || fail "heidi --json status produced no output"
expect_json_only "$OUT" <<<"$OUT"
echo "OK"

echo ""
echo "=== Test 4: JSON integrity (connect status --json) ==="
OUT=$($HEIDI_CMD connect status --json 2>/dev/null) || fail "connect status --json (exit=$?)"
[ -n "$OUT" ] || fail "connect status --json produced no output"
expect_json_only "$OUT" <<<"$OUT"
echo "OK"

echo ""
echo "=== Test 5: env still works (HEIDI_PLAIN=1) ==="
HEIDI_PLAIN=1 $HEIDI_CMD setup || true

echo ""
echo "=== Test 6: env still works (NO_COLOR=1) ==="
NO_COLOR=1 $HEIDI_CMD setup || true

echo ""
echo "=== Test 7: StreamingUI safety (non-interactive) ==="
PYTHONPATH=src python3 -c "from heidi_cli.streaming import StreamingUI; ui=StreamingUI(disable=False); ui.start('t'); ui.update('ok'); ui.stop('done')" || fail "StreamingUI snippet failed"

echo ""
echo "=========================================="
echo "Smoke checks completed."
echo ""
echo "JSON Support Notes:"
echo "  - Global --json works with: status"
echo "  - Per-command --json works with: connect status"
echo "  - Commands without JSON: doctor, paths (use --plain for text output)"
echo ""
echo "Manual Ctrl+C checks to run:"
echo "  - $HEIDI_CMD setup  (press Ctrl+C during Step 2 spinner)"
echo "  - $HEIDI_CMD auth device  (press Ctrl+C during polling spinner)"
echo "PASS looks like:"
echo "  - cursor is visible"
echo "  - prompt accepts typing immediately"
echo "  - no stuck styling (colors), no spinner characters left behind"
