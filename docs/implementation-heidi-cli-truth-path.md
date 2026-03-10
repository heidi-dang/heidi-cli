# Implementation: Heidi CLI Truth Path Commands

## Overview
This document describes the implementation of heidi-cli truth path commands that provide the single source of truth for heidi-engine dashboard.

## Commands Implemented

### 1. `heidi truth get_status_field`

Gets current status fields for a run.

**Command:**
```bash
heidi truth get_status_field <RUN_ID> [--timeout SECONDS]
```

**Output Format:** JSON (one line)
```json
{"run_id": "proof_test2", "status": "running", "current_stage": "generate", "counters": {"teacher_generated": 10}}
```

**Timeout Behavior:**
- Default: 5 seconds
- Returns default status on timeout
- Reads from `AUTOTRAIN_DIR/runs/<run_id>/state.json`
- Falls back to default values if no state file found

### 2. `heidi truth stream_events`

Streams events for a run.

**Command:**
```bash
heidi truth stream_events <RUN_ID> [--timeout SECONDS] [--limit COUNT]
```

**Output Format:** JSON Lines (one JSON object per line)
```json
{"event_version": "1.0", "ts": "2026-03-08T03:13:30.533577", "run_id": "proof_test2", "stage": "generate", "event_type": "progress", "message": "First event"}
```

**Timeout Behavior:**
- Default: 5 seconds  
- Returns immediately on timeout (no hanging)
- Returns empty if no events found
- Respects --limit flag (default: 20)

## Dashboard Integration

The heidi-engine dashboard uses these commands as the single truth path:

```python
# In dashboard.py - load_state()
result = subprocess.run(
    ["heidi", "truth", "get_status_field", run_id],
    capture_output=True, text=True, timeout=5
)
if result.returncode == 0 and result.stdout.strip():
    return json.loads(result.stdout)

# In dashboard.py - load_new_events()
result = subprocess.run(
    ["heidi", "truth", "stream_events", run_id],
    capture_output=True, text=True, timeout=5
)
```

## Verified Behavior

### Proof 1: State Reading
```bash
$ heidi truth get_status_field proof_test
{
    "run_id": "proof_test",
    "status": "running",
    "current_stage": "generate",
    "counters": {
        "teacher_generated": 10,
        "teacher_failed": 1
    }
}
```
✅ Returns real telemetry state from state.json

### Proof 2: Event Streaming
```bash
$ heidi truth stream_events proof_test2 --limit 1
{"event_version": "1.0", "ts": "2026-03-08T03:13:30.533577", "run_id": "proof_test2", "stage": "generate", "event_type": "progress", "message": "First event"}
```
✅ Returns real events from events.jsonl

### Proof 3: Doctor Check
```bash
$ python -m tools.doctor_heidi_truth
[DOCTOR-TRUTH] PASS - All truth path commands verified
```

## Fallback Rules

If `heidi` CLI is unavailable:
1. `get_status_field` returns default status with run_id
2. `stream_events` returns empty (no output)
3. Dashboard falls back to direct file reads

## Allowlisted Fields

The following fields are exposed by `get_status_field`:

- `run_id` - Run identifier
- `status` - Current status (unknown, running, paused, stopped, completed, error)
- `current_round` - Current round number
- `current_stage` - Current stage (initializing, generate, validate, train, eval)
- `stop_requested` - Whether stop was requested
- `pause_requested` - Whether pause was requested
- `counters.*` - All counter values
- `usage.*` - All usage metrics

## Error Handling

- **Command not found**: Dashboard falls back to direct file reads
- **Timeout**: Returns default/empty values, doesn't hang (5 second timeout)
- **Invalid JSON**: Treated as command failure, falls back
- **No events**: Returns empty (not an error)
