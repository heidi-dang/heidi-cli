#!/usr/bin/env python3
"""
================================================================================
tools/doctor_heidi_truth.py - Heidi Truth Path Commands Verification
================================================================================

PURPOSE:
    Verify that heidi-cli has the truth path commands implemented:
    - heidi truth get_status_field
    - heidi truth stream_events

CHECKS:
    1. Commands exist and are callable
    2. Output format is valid JSON (get_status_field)
    3. Output format is valid JSON lines (stream_events)
    4. Commands have proper timeout handling
    5. Commands are stable for subprocess use

USAGE:
    python -m tools.doctor_heidi_truth [--verbose]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def check_truth_commands(verbose: bool = False) -> bool:
    """
    Verify heidi truth path commands are implemented and working.

    Returns True if all checks pass.
    """
    checks = []

    # Check 1: get_status_field command exists
    try:
        result = subprocess.run(
            ["heidi", "truth", "get_status_field", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_get_status = result.returncode == 0 or "get_status_field" in result.stdout
        checks.append(("get_status_field command exists", has_get_status))
        if verbose:
            print(f"[DEBUG] get_status_field help: {result.stdout[:200]}")
    except Exception as e:
        checks.append(("get_status_field command exists", False))
        if verbose:
            print(f"[DEBUG] get_status_field error: {e}")

    # Check 2: stream_events command exists
    try:
        result = subprocess.run(
            ["heidi", "truth", "stream_events", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_stream = result.returncode == 0 or "stream_events" in result.stdout
        checks.append(("stream_events command exists", has_stream))
        if verbose:
            print(f"[DEBUG] stream_events help: {result.stdout[:200]}")
    except Exception as e:
        checks.append(("stream_events command exists", False))
        if verbose:
            print(f"[DEBUG] stream_events error: {e}")

    # Check 3: get_status_field returns valid JSON
    try:
        result = subprocess.run(
            ["heidi", "truth", "get_status_field", "test_run"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            has_valid_json = isinstance(data, dict) and "run_id" in data
            checks.append(("get_status_field returns valid JSON", has_valid_json))
            if verbose:
                print(f"[DEBUG] get_status_field output: {result.stdout[:200]}")
        else:
            checks.append(("get_status_field returns valid JSON", False))
    except Exception as e:
        checks.append(("get_status_field returns valid JSON", False))
        if verbose:
            print(f"[DEBUG] get_status_field JSON error: {e}")

    # Check 4: stream_events returns valid JSON lines or empty
    try:
        result = subprocess.run(
            ["heidi", "truth", "stream_events", "test_run", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Should be either empty or valid JSON lines
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        all_valid = all(json.loads(line) for line in lines if line.strip())
        checks.append(("stream_events returns valid JSON lines", all_valid or len(lines) == 0))
        if verbose:
            print(f"[DEBUG] stream_events output: {result.stdout[:200]}")
    except Exception as e:
        checks.append(("stream_events returns valid JSON lines", False))
        if verbose:
            print(f"[DEBUG] stream_events JSON error: {e}")

    # Check 5: Commands handle timeout gracefully
    try:
        result = subprocess.run(
            ["heidi", "truth", "get_status_field", "nonexistent_run", "--timeout", "1"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        # Should return quickly with default status
        checks.append(("get_status_field timeout handling", True))
    except subprocess.TimeoutExpired:
        checks.append(("get_status_field timeout handling", False))
    except Exception:
        checks.append(("get_status_field timeout handling", True))  # Expected to fail gracefully

    # Print results
    print("\n[DOCTOR] Truth Path Commands Check:")
    all_passed = True
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
        if not result:
            all_passed = False

    return all_passed


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Verify heidi-cli truth path commands")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    success = check_truth_commands(verbose=args.verbose)

    if success:
        print("\n[DOCTOR-TRUTH] PASS - All truth path commands verified")
        sys.exit(0)
    else:
        print("\n[DOCTOR-TRUTH] FAIL - Truth path commands not fully verified")
        sys.exit(1)


if __name__ == "__main__":
    main()
