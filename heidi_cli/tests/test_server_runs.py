
import pytest
import json
import os
import time
from fastapi.testclient import TestClient
from heidi_cli.server import app
from heidi_cli.config import ConfigManager

# Mock ConfigManager
@pytest.fixture
def mock_runs_dir(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    original_runs_dir = ConfigManager.runs_dir
    ConfigManager.runs_dir = staticmethod(lambda: runs_dir)

    # Attempt to reset RunCache if it exists (for when we add it)
    try:
        from heidi_cli.server import RunCache
        if hasattr(RunCache, "_instance"):
            RunCache._instance = None
    except ImportError:
        pass

    yield runs_dir

    ConfigManager.runs_dir = original_runs_dir
    try:
        from heidi_cli.server import RunCache
        if hasattr(RunCache, "_instance"):
            RunCache._instance = None
    except ImportError:
        pass

def create_run(runs_dir, run_id, status="completed", mtime_offset=0):
    run_dir = runs_dir / run_id
    run_dir.mkdir(exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({"status": status, "task": f"task {run_id}"}))
    # Set mtime
    t = time.time() - mtime_offset
    os.utime(run_dir, (t, t))
    return run_dir

def test_list_runs_empty(mock_runs_dir):
    client = TestClient(app)
    response = client.get("/runs")
    assert response.status_code == 200
    assert response.json() == []

def test_list_runs_single(mock_runs_dir):
    create_run(mock_runs_dir, "run1")
    client = TestClient(app)
    response = client.get("/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "run1"
    assert data[0]["status"] == "completed"

def test_list_runs_sorting(mock_runs_dir):
    # run1 is oldest, run2 is newest
    create_run(mock_runs_dir, "run1", mtime_offset=100)
    create_run(mock_runs_dir, "run2", mtime_offset=0)

    client = TestClient(app)
    response = client.get("/runs")
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_id"] == "run2"
    assert data[1]["run_id"] == "run1"

def test_list_runs_limit(mock_runs_dir):
    for i in range(5):
        create_run(mock_runs_dir, f"run{i}", mtime_offset=i) # run0 is newest

    client = TestClient(app)
    response = client.get("/runs?limit=2")
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_id"] == "run0"
    assert data[1]["run_id"] == "run1"

def test_cache_update_on_new_run(mock_runs_dir):
    create_run(mock_runs_dir, "run1")
    client = TestClient(app)
    assert len(client.get("/runs").json()) == 1

    # Add new run
    create_run(mock_runs_dir, "run2")
    # Should detect new run because runs_dir mtime changes
    assert len(client.get("/runs").json()) == 2

def test_cache_update_on_run_modification(mock_runs_dir):
    # This tests the limitation/feature.
    # If run.json is modified, status should update for top runs.
    create_run(mock_runs_dir, "run1", status="running")
    client = TestClient(app)
    data = client.get("/runs").json()
    assert data[0]["status"] == "running"

    # Update run.json
    (mock_runs_dir / "run1" / "run.json").write_text(json.dumps({"status": "failed"}))

    # Should reflect change immediately because we read run.json for top items
    data = client.get("/runs").json()
    assert data[0]["status"] == "failed"
