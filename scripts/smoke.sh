#!/bin/bash
set -e

echo "=========================================="
echo "Heidi CLI Smoke Test"
echo "=========================================="

HEIDI_CMD="${HEIDI_CMD:-heidi}"
BACKEND_PORT="${BACKEND_PORT:-7777}"
UI_PORT="${UI_PORT:-3002}"
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
UI_URL="http://127.0.0.1:$UI_PORT"

FAILED=0

cleanup() {
    echo ""
    echo "Cleaning up..."
    $HEIDI_CMD stop 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "=== Test 1: heidi paths ==="
OUTPUT=$($HEIDI_CMD paths 2>&1) || true
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "Config"; then
    echo "✓ heidi paths shows Config"
else
    echo "✗ heidi paths failed"
    FAILED=1
fi

echo ""
echo "=== Test 2: Start backend ==="
$HEIDI_CMD start backend &
BACKEND_PID=$!
sleep 5

if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "✓ Backend is running on port $BACKEND_PORT"
else
    echo "✗ Backend failed to start"
    FAILED=1
fi

echo ""
echo "=== Test 3: Start UI ==="
$HEIDI_CMD start ui &
UI_PID=$!
sleep 8

if curl -s "$UI_URL" > /dev/null 2>&1; then
    echo "✓ UI is running on port $UI_PORT"
else
    echo "✗ UI failed to start"
    FAILED=1
fi

echo ""
echo "=== Test 4: Health check through UI ==="
UI_HEALTH=$(curl -s "$UI_URL/api/health" 2>/dev/null || echo "failed")
if echo "$UI_HEALTH" | grep -q "ok\|healthy\|true"; then
    echo "✓ UI health check passed"
else
    echo "✗ UI health check failed: $UI_HEALTH"
    FAILED=1
fi

echo ""
echo "=== Test 5: Stop services cleanly ==="
$HEIDI_CMD stop
sleep 2
echo "✓ Services stopped"

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "All smoke tests passed!"
    exit 0
else
    echo "Some tests failed!"
    exit 1
fi
