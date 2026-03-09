import pytest
import shutil
from pathlib import Path

class MockConfig:
    data_root = Path("/tmp/test_heidi_data")
    state_dirs = {
        "registry": Path("/tmp/test_heidi_data/registry"),
        "models_stable": Path("/tmp/test_heidi_data/models/stable/versions"),
        "models_candidate": Path("/tmp/test_heidi_data/models/candidate/versions"),
        "models_experimental": Path("/tmp/test_heidi_data/models/experimental/versions"),
        "evals": Path("/tmp/test_heidi_data/evals")
    }
    models = []
    promotion_policy = "beat_stable"

@pytest.fixture(autouse=True)
def setup_test_dirs(monkeypatch):
    monkeypatch.setattr("heidi_cli.shared.config.ConfigLoader.load", lambda: MockConfig())
    if MockConfig.data_root.exists():
        shutil.rmtree(MockConfig.data_root)
    for path in MockConfig.state_dirs.values():
        path.mkdir(parents=True, exist_ok=True)
        
    # Reset registry singleton
    from heidi_cli.registry.manager import model_registry
    model_registry.registry_root = MockConfig.state_dirs["registry"]
    model_registry.registry_file = model_registry.registry_root / "registry.json"
    if model_registry.registry_file.exists():
        model_registry.registry_file.unlink()
    model_registry._init_registry()
    yield
    if MockConfig.data_root.exists():
        shutil.rmtree(MockConfig.data_root)

def test_registry_registration_and_promotion():
    import asyncio
    asyncio.run(_test_registry_registration_and_promotion())

async def _test_registry_registration_and_promotion():
    from heidi_cli.registry.manager import model_registry
    
    # Register experimental
    vid1 = await model_registry.register_version("v1_exp", Path("/tmp/dummy"))
    reg = model_registry.load_registry()
    assert "v1_exp" in reg["versions"]
    assert reg["versions"]["v1_exp"]["channel"] == "experimental"
    
    # Promote to candidate
    await model_registry.promote("v1_exp", "candidate")
    reg = model_registry.load_registry()
    assert reg["versions"]["v1_exp"]["channel"] == "candidate"
    assert reg["active_candidate"] == "v1_exp"
    
    # Promote to stable
    await model_registry.promote("v1_exp", "stable")
    reg = model_registry.load_registry()
    assert reg["versions"]["v1_exp"]["channel"] == "stable"
    assert reg["active_stable"] == "v1_exp"

def test_eval_harness():
    import asyncio
    asyncio.run(_test_eval_harness())

async def _test_eval_harness():
    from heidi_cli.registry.manager import model_registry
    from heidi_cli.registry.eval import eval_harness
    
    await model_registry.register_version("v1_stable", Path("/tmp/dummy"), channel="stable")
    await model_registry.promote("v1_stable", "stable")
    
    await model_registry.register_version("v2_cand", Path("/tmp/dummy"), channel="experimental")
    await model_registry.promote("v2_cand", "candidate")
    
    passed, results = await eval_harness.evaluate_candidate("v2_cand")
    assert passed is True
    assert results["candidate_id"] == "v2_cand"

def test_hotswap_manager(monkeypatch):
    import asyncio
    asyncio.run(_test_hotswap_manager(monkeypatch))

async def _test_hotswap_manager(monkeypatch):
    from heidi_cli.registry.manager import model_registry
    from heidi_cli.registry.hotswap import hotswap_manager
    
    await model_registry.register_version("v1_stable", Path("/tmp/dummy"), channel="stable")
    await model_registry.promote("v1_stable", "stable")
    
    success = await hotswap_manager.reload_stable_model()
    assert success is True
    
    # Simulate no stable model
    data = model_registry.load_registry()
    data["active_stable"] = None
    model_registry.save_registry(data)
    
    success2 = await hotswap_manager.reload_stable_model()
    assert success2 is False
