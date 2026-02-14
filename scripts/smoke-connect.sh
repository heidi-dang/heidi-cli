#!/bin/bash
set -e

echo "=== Heidi Connect Smoke Test ==="

HEIDI_CMD="${HEIDI_CMD:-heidi}"

# Test 1: heidi connect status
echo "[1/3] Testing heidi connect status..."
$HEIDI_CMD connect status

# Test 2: heidi connect ollama (will fail if not running, but should handle gracefully)
echo ""
echo "[2/3] Testing heidi connect ollama..."
$HEIDI_CMD connect ollama --url http://127.0.0.1:11434 --no-save || echo "Ollama not running (expected)"

# Test 3: heidi connect opencode local
echo ""
echo "[3/3] Testing heidi connect opencode --mode local..."
$HEIDI_CMD connect opencode --mode local --no-save

echo ""
echo "=== Connect Smoke Test Complete ==="
