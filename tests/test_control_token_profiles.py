from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "bootstrap-control-token.py"
spec = importlib.util.spec_from_file_location("bootstrap_control_token", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_standard_profile_can_bootstrap_but_not_external_execute_or_delete():
    scopes = set(module.scopes_for_profile("standard"))
    assert "workspace:read" in scopes
    assert "workspace:provision" in scopes
    assert "coding:write" in scopes
    assert "command:external" not in scopes
    assert "workspace:delete" not in scopes


def test_owner_full_profile_adds_external_execution_and_workspace_delete():
    scopes = set(module.scopes_for_profile("owner-full"))
    assert "workspace:provision" in scopes
    assert "command:external" in scopes
    assert "workspace:delete" in scopes


def test_legacy_full_profile_is_exact_alias_of_owner_full():
    assert module.scopes_for_profile("full") == module.scopes_for_profile("owner-full")
