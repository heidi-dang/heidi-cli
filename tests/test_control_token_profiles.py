from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "control_token_profiles.py"
spec = importlib.util.spec_from_file_location("control_token_profiles", MODULE_PATH)
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


def test_developer_profile_adds_external_execution_without_workspace_delete():
    scopes = set(module.scopes_for_profile("developer"))
    assert "workspace:provision" in scopes
    assert "command:execute" in scopes
    assert "command:external" in scopes
    assert "workspace:delete" not in scopes


def test_owner_full_profile_adds_external_execution_and_workspace_delete():
    scopes = set(module.scopes_for_profile("owner-full"))
    assert "workspace:provision" in scopes
    assert "command:external" in scopes
    assert "workspace:delete" in scopes


def test_legacy_full_profile_is_exact_alias_of_owner_full():
    assert module.normalize_profile("full") == "owner-full"
    assert module.scopes_for_profile("full") == module.scopes_for_profile("owner-full")


def test_unknown_profile_fails_closed():
    with pytest.raises(ValueError, match="unsupported control profile"):
        module.scopes_for_profile("unrestricted")
