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
echo "=== Test 2: Backend health ==="
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
echo "=== Test 3: Auth status (logged out) ==="
AUTH_STATUS=$(curl -s "$BACKEND_URL/auth/status" 2>/dev/null || echo "{}")
echo "Auth status: $AUTH_STATUS"
if echo "$AUTH_STATUS" | grep -q '"authenticated":false\|"authenticated": false'; then
    echo "✓ Auth status shows logged out"
else
    echo "✗ Auth status check failed"
    FAILED=1
fi

echo ""
echo "=== Test 4: Auth required mode (if enabled) ==="
HEIDI_AUTH_MODE=required curl -s "$BACKEND_URL/run" > /dev/null 2>&1
RUN_STATUS=$?
if [ $RUN_STATUS -eq 401 ]; then
    echo "✓ Auth required mode blocks /run when logged out"
else
    echo "✗ Auth required mode did not block /run (status: $RUN_STATUS)"
fi

echo ""
echo "=== Test 5: UI static serving ==="
UI_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/ui/" 2>/dev/null || echo "000")
if [ "$UI_RESPONSE" = "200" ]; then
    echo "✓ UI /ui/ returns 200"
else
    echo "✗ UI /ui/ returned $UI_RESPONSE"
    FAILED=1
fi

echo ""
echo "=== Test 6: UI deep link (SPA routing) ==="
UI_DEEP=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/ui/settings" 2>/dev/null || echo "000")
if [ "$UI_DEEP" = "200" ]; then
    echo "✓ UI deep link /ui/settings returns 200"
else
    echo "✗ UI deep link returned $UI_DEEP"
    FAILED=1
fi

echo ""
echo "=== Test 7: CORS headers (no wildcard) ==="
CORS_ORIGIN=$(curl -s -I "$BACKEND_URL/health" 2>/dev/null | grep -i "access-control-allow-origin" || echo "")
echo "CORS header: $CORS_ORIGIN"
if echo "$CORS_ORIGIN" | grep -q "localhost\|127.0.0.1" && ! echo "$CORS_ORIGIN" | grep -q '"\*"'; then
    echo "✓ CORS is properly configured (not wildcard)"
else
    echo "✗ CORS may be misconfigured"
    FAILED=1
fi

echo ""
echo "=== Test 8: Start UI ==="
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
echo "=== Test 9: Health check through UI proxy ==="
UI_HEALTH=$(curl -s "$UI_URL/api/health" 2>/dev/null || echo "failed")
if echo "$UI_HEALTH" | grep -q "ok\|healthy\|true"; then
    echo "✓ UI health check passed (proxy working)"
else
    echo "✗ UI health check failed: $UI_HEALTH"
    FAILED=1
fi

echo ""
echo "=== Test 10: Stop services cleanly ==="
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
