import pytest
import asyncio
import json
import shutil
from pathlib import Path

class MockConfig:
    data_root = Path("/tmp/test_heidi_data")
    state_dirs = {
        "datasets_raw": Path("/tmp/test_heidi_data/datasets/raw"),
        "datasets_curated": Path("/tmp/test_heidi_data/datasets/curated")
    }

@pytest.fixture(autouse=True)
def setup_test_dirs(monkeypatch):
    monkeypatch.setattr("heidi_cli.shared.config.ConfigLoader.load", lambda: MockConfig())
    if MockConfig.data_root.exists():
        shutil.rmtree(MockConfig.data_root)
    MockConfig.state_dirs["datasets_raw"].mkdir(parents=True, exist_ok=True)
    MockConfig.state_dirs["datasets_curated"].mkdir(parents=True, exist_ok=True)
    yield
    if MockConfig.data_root.exists():
        shutil.rmtree(MockConfig.data_root)

def test_pipeline_capture_and_curate():
    asyncio.run(_test_pipeline_capture_and_curate())

async def _test_pipeline_capture_and_curate():
    from heidi_cli.pipeline.capture import capture_engine
    from heidi_cli.pipeline.curation import curation_engine
    
    # 1. Capture a raw run with secrets
    messages = [
        {"role": "user", "content": "Here is my key: sk-abcdefghijklmnopqrstuvwxyz1234567890abcdef"},
        {"role": "assistant", "content": "I see your token: ghp_abcdefghijklmnopqrstuvwxyz1234567890"}
    ]
    response = {"status": "ok", "nested": {"password": "supersecretpassword123", "normal": "value"}}
    
    run_id = await capture_engine.capture_run("test_task", messages, response)
    
    # 2. Curate the dataset
    count = await curation_engine.curate_dataset()
    assert count == 1
    
    # 3. Read the curated dataset and assert schema and redaction
    curated_files = list(MockConfig.state_dirs["datasets_curated"].glob("*.jsonl"))
    assert len(curated_files) == 1
    
    with open(curated_files[0], "r") as f:
        line = f.readline()
        curated_data = json.loads(line)
        
    # Check schema
    assert "messages" in curated_data
    assert "response" in curated_data
    assert curated_data["run_id"] == run_id
    
    # Check OpenAI redaction
    assert "sk-" not in curated_data["messages"][0]["content"]
    assert "[REDACTED]" in curated_data["messages"][0]["content"]
    
    # Check GitHub redaction
    assert "ghp_" not in curated_data["messages"][1]["content"]
    assert "[REDACTED]" in curated_data["messages"][1]["content"]
    
    # Check generic / nested password redaction
    assert "password" in curated_data["response"]["nested"]
    assert "[REDACTED]" == curated_data["response"]["nested"]["password"]
    assert curated_data["response"]["nested"]["normal"] == "value"
    
def test_text_redaction():
    from heidi_cli.pipeline.curation import CurationEngine
    engine = CurationEngine()
    
    text1 = "My token is sk-abc123def456ghi789jkl012mno345pqr678stu901vw please guard it."
    assert "sk-" not in engine.redact_text(text1)
    
    text2 = "API_KEY='secrettoken12345678' in my config"
    assert "secrettoken" not in engine.redact_text(text2)
