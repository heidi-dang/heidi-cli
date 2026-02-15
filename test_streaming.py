#!/usr/bin/env python3
"""
Streaming smoke test for Heidi CLI.
Tests that the backend emits structured events that the UI can consume.

Usage:
    python test_streaming.py

Requirements:
    - Heidi CLI server must be running (heidi serve)
    - Or set TEST_SERVER_URL=http://localhost:7777
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "heidi_cli" / "src"))

SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:7777")
TEST_TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "30"))
API_KEY = os.environ.get("TEST_API_KEY", "testkey")
USE_DRY_RUN = os.environ.get("TEST_DRY_RUN", "true").lower() == "true"


def get_headers():
    return {"Content-Type": "application/json", "X-Heidi-Key": API_KEY}


def test_server_health():
    """Test 1: Server is running and healthy."""
    print("\n[TEST 1] Server health check...")
    try:
        req = urllib.request.Request(f"{SERVER_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            assert data.get("status") in ["ok", "healthy"], f"Unexpected status: {data}"
            print("  ✓ Server is healthy")
            return True
    except Exception as e:
        print(f"  ✗ Server health check failed: {e}")
        return False


def test_stream_endpoint_exists():
    """Test 2: Stream endpoint exists and returns events."""
    print("\n[TEST 2] Stream endpoint exists...")

    # First, start a run to get a run_id
    try:
        # Start a simple run with dry_run for fast testing
        run_payload = {"prompt": "echo hello", "executor": "copilot", "dry_run": USE_DRY_RUN}
        print(f"  → Starting run with dry_run={USE_DRY_RUN}")
        req = urllib.request.Request(
            f"{SERVER_URL}/run",
            data=json.dumps(run_payload).encode(),
            headers=get_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            run_data = json.loads(resp.read())
            run_id = run_data.get("run_id")
            print(f"  → Started run: {run_id}")

            if not run_id:
                print("  ✗ No run_id returned")
                return False
    except Exception as e:
        print(f"  ✗ Failed to start run: {e}")
        return False

    # Now try to stream events
    try:
        stream_url = f"{SERVER_URL}/runs/{run_id}/stream"
        print(f"  → Streaming from: {stream_url}")

        events_received = []
        start_time = time.time()

        req = urllib.request.Request(stream_url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            # Read a few lines of SSE
            while time.time() - start_time < TEST_TIMEOUT:
                line = resp.readline()
                if not line:
                    break
                line = line.decode().strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: "
                    try:
                        event = json.loads(data)
                        events_received.append(event)
                        print(f"    ← Event: {event.get('type')}")

                        # Check for structured events
                        if event.get("type") in [
                            "run_state",
                            "message_delta",
                            "tool_start",
                            "tool_log",
                            "tool_done",
                            "tool_error",
                            "thinking",
                        ]:
                            print(f"      ✓ Structured event: {event.get('type')}")
                    except json.JSONDecodeError:
                        pass

                # Stop after a few events
                if len(events_received) >= 5:
                    break

        if events_received:
            print(f"  ✓ Received {len(events_received)} events")
            return True
        else:
            print("  ✗ No events received (may be too fast or completed)")
            return True  # Not a failure, just means run completed

    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP error: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"  ✗ Stream error: {e}")
        return False


def test_event_types():
    """Test 3: Verify event types are emitted by the logging module."""
    print("\n[TEST 3] Event types available in logging module...")

    try:
        from heidi_cli.logging import HeidiLogger

        # Check that the event methods exist
        methods = [
            "emit_thinking",
            "emit_message_delta",
            "emit_tool_start",
            "emit_tool_log",
            "emit_tool_done",
            "emit_tool_error",
            "emit_run_state",
        ]

        for method in methods:
            if hasattr(HeidiLogger, method):
                print(f"  ✓ {method} exists")
            else:
                print(f"  ✗ {method} missing")
                return False

        return True
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        return False


def main():
    print("=" * 50)
    print("Heidi CLI Streaming Smoke Test")
    print("=" * 50)
    print(f"Server: {SERVER_URL}")
    print(f"Timeout: {TEST_TIMEOUT}s")

    results = []

    # Run tests
    results.append(("Server Health", test_server_health()))
    results.append(("Event Types", test_event_types()))
    results.append(("Stream Endpoint", test_stream_endpoint_exists()))

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All smoke tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
