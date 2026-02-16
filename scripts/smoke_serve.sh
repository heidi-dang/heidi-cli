#!/usr/bin/env bash
# smoke_serve.sh - Acceptance tests for heidi serve command
set -euo pipefail

HEIDI_CMD="${HEIDI_CMD:-python3 -m src.heidi_cli.cli}"
PORT=17777
BASE_URL="http://127.0.0.1:${PORT}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

cleanup() {
  echo "Cleaning up..."
  pkill -f "heidi serve" 2>/dev/null || true
  pkill -f "uvicorn.*${PORT}" 2>/dev/null || true
  rm -f /home/heidi/.local/state/heidi/server.pid 2>/dev/null || true
}
trap cleanup EXIT

echo "=========================================="
echo "Heidi CLI Smoke: serve command"
echo "=========================================="

echo ""
echo "=== Test 1: heidi --version ==="
$HEIDI_CMD --version || fail "--version failed"

echo ""
echo "=== Test 2: heidi doctor ==="
$HEIDI_CMD doctor || fail "doctor failed"

echo ""
echo "=== Test 3: heidi serve --plain (foreground) ==="
echo "Starting server on port ${PORT}..."
timeout 5 $HEIDI_CMD serve --port ${PORT} --plain &
SERVER_PID=$!
sleep 3

echo "Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s "${BASE_URL}/health" || echo "FAILED")
echo "Health response: $HEALTH_RESPONSE"
if [[ "$HEALTH_RESPONSE" != *"healthy"* ]] && [[ "$HEALTH_RESPONSE" != *"ok"* ]]; then
  fail "Health check failed: $HEALTH_RESPONSE"
fi

echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
sleep 1

echo ""
echo "=== Test 4: heidi serve --detach ==="
echo "Starting detached server..."
$HEIDI_CMD serve --port ${PORT} --detach --plain
sleep 3

echo "Checking if server is running..."
HEALTH_RESPONSE=$(curl -s "${BASE_URL}/health" || echo "FAILED")
echo "Health response: $HEALTH_RESPONSE"
if [[ "$HEALTH_RESPONSE" != *"healthy"* ]] && [[ "$HEALTH_RESPONSE" != *"ok"* ]]; then
  fail "Detached server health check failed: $HEALTH_RESPONSE"
fi

DETACHED_PID=$(cat /home/runner/.local/state/heidi/server.pid 2>/dev/null || cat ~/.local/state/heidi/server.pid 2>/dev/null || echo "")
if [[ -n "$DETACHED_PID" ]]; then
  echo "Server PID: $DETACHED_PID"
fi

echo ""
echo "=== Test 5: HEIDI_PLAIN=1 environment ==="
HEIDI_PLAIN=1 timeout 5 $HEIDI_CMD serve --port $((PORT+1)) &
SERVER_PID=$!
sleep 3
HEALTH_RESPONSE=$(curl -s "http://127.0.0.1:$((PORT+1))/health" || echo "FAILED")
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
if [[ "$HEALTH_RESPONSE" != *"healthy"* ]] && [[ "$HEALTH_RESPONSE" != *"ok"* ]]; then
  fail "HEIDI_PLAIN=1 health check failed: $HEALTH_RESPONSE"
fi

echo ""
echo "=========================================="
echo "ALL TESTS PASSED"
echo "=========================================="
