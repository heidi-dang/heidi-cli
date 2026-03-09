import pytest
import asyncio
from pathlib import Path

# Mock config so the test database goes to an in-memory or throwaway location
class MockConfig:
    data_root = Path("/tmp/test_heidi_data")
    memory_sqlite_path = Path("/tmp/test_heidi_data/memory.db")
    model_host_enabled = True
    models = []

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    monkeypatch.setattr("heidi_cli.shared.config.ConfigLoader.load", lambda: MockConfig())
    # Ensure local dir is clean for file operations
    if MockConfig.memory_sqlite_path.exists():
        MockConfig.memory_sqlite_path.unlink()
    MockConfig.data_root.mkdir(parents=True, exist_ok=True)
    
    # Reset DatabaseManager to use file DB for tests to isolate them
    from heidi_cli.runtime.db import db
    db.db_path = MockConfig.memory_sqlite_path
    db.init_schema()
    
    yield
    if MockConfig.memory_sqlite_path.exists():
        MockConfig.memory_sqlite_path.unlink()

def test_memory_retrieval_and_writing():
    asyncio.run(_test_memory_retrieval_and_writing())

async def _test_memory_retrieval_and_writing():
    from heidi_cli.runtime.db import db
    conn = db.get_connection()
    
    # Write a reflection/rule
    conn.execute(
        "INSERT INTO rules (id, rule_text) VALUES (?, ?)",
        ("rule-1", "Always validate user input first.")
    )
    conn.commit()
    
    # Retrieve it
    cursor = conn.execute("SELECT rule_text FROM rules LIMIT 1")
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == "Always validate user input first."
    
def test_reflection_engine(monkeypatch):
    asyncio.run(_test_reflection_engine(monkeypatch))

async def _test_reflection_engine(monkeypatch):
    from heidi_cli.runtime.reflection import ReflectionEngine
    engine = ReflectionEngine()
    
    # Set up some dummy episodes
    from heidi_cli.runtime.db import db
    conn = db.get_connection()
    conn.execute("INSERT INTO episodes (id, run_id, task, steps, outcome) VALUES (?, ?, ?, ?, ?)",
                 ("ep-123", "run-123", "sort array", "[]", "success"))
    conn.commit()
    
    # Call reflect (this parses outcome to inject into rules/reflections)
    # The current basic implementation of reflect_on_run uses dummy generation
    ref_id = await engine.reflect_on_run("run-123", "sort array", "success")
    assert isinstance(ref_id, str) and len(ref_id) > 10
    
    # verify it wrote to db (Basic engine writes dummy conclusion currently)
    res = conn.execute("SELECT conclusion FROM reflections WHERE id=?", (ref_id,)).fetchone()
    assert res is not None
    assert "success" in res[0].lower()

def test_reward_scorer_and_strategy():
    asyncio.run(_test_reward_scorer_and_strategy())

async def _test_reward_scorer_and_strategy():
    from heidi_cli.runtime.reward import RewardScorer
    from heidi_cli.runtime.strategy import StrategySelector
    from heidi_cli.runtime.db import db

    scorer = RewardScorer()
    selector = StrategySelector()

    # Log a successful reward event
    await scorer.record_reward("run-456", "model-X", 0.9, "refactoring")
    conn = db.get_connection()
    
    # Verify reward_events
    count = conn.execute("SELECT COUNT(*) FROM reward_events WHERE run_id='run-456'").fetchone()[0]
    assert count == 1
    
    # Verify strategy_stats updated
    stat = conn.execute("SELECT total_runs, avg_reward FROM strategy_stats WHERE strategy_id='model-X'").fetchone()
    assert stat is not None
    assert stat[0] == 1 # runs
    assert round(stat[1], 1) == 0.9

    # Test selection logic (epsilon greedy mock usage)
    # Give model-Y a higher reward
    await scorer.record_reward("run-789", "model-Y", 1.0, "refactoring")
    
    # We can't deterministically test epsilon greedy easily without patching random,
    # but we can ensure the selector runs without errors and returns a known model from config.
    available_models = ["model-X", "model-Y"]
    
    selected = selector.select_best_model(available_models)
    assert selected in available_models
