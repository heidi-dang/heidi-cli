import importlib.util
import json
import os
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "lifecycle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("heidi_lifecycle", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_redact_mapping_never_emits_secret_values():
    module = load_module()
    value = module.redact_mapping(
        {
            "HEIDI_MODE": "production",
            "CPTR_API_TOKEN": "sk-cptr-super-secret",
            "nested": {"password": "secret", "url": "https://example.com"},
        }
    )
    encoded = json.dumps(value)
    assert "sk-cptr-super-secret" not in encoded
    assert '"CPTR_API_TOKEN": "<redacted>"' in encoded
    assert '"password": "<redacted>"' in encoded
    assert value["HEIDI_MODE"] == "production"


def test_validate_tar_members_rejects_absolute_and_parent_traversal(tmp_path: Path):
    module = load_module()
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as handle:
        info = tarfile.TarInfo("../escape")
        info.size = 0
        handle.addfile(info)
    with tarfile.open(archive, "r") as handle:
        try:
            module.validate_tar_members(handle)
        except ValueError as exc:
            assert "unsafe" in str(exc).lower()
        else:
            raise AssertionError("parent traversal must be rejected")


def test_parse_state_reads_quoted_env_without_executing_shell(tmp_path: Path):
    module = load_module()
    state = tmp_path / "state.env"
    state.write_text('HEIDI_MODE="production"\nHEIDI_MCP_URL="https://mcp.example.com/mcp"\n', encoding="utf-8")
    parsed = module.parse_state(state)
    assert parsed == {
        "HEIDI_MODE": "production",
        "HEIDI_MCP_URL": "https://mcp.example.com/mcp",
    }


def make_release(home: Path, version: str, channel: str = "stable") -> Path:
    release = home / "releases" / version
    (release / "source" / "release").mkdir(parents=True)
    (release / "source" / "scripts").mkdir(parents=True)
    (release / "source" / "release" / "compatibility.json").write_text(
        json.dumps({"heidi_version": version}) + "\n", encoding="utf-8"
    )
    (release / "heidi-release.json").write_text(
        json.dumps({"version": version, "channel": channel}) + "\n", encoding="utf-8"
    )
    return release


def test_rollback_updates_state_and_current_symlink_atomically(tmp_path: Path, monkeypatch):
    module = load_module()
    config = tmp_path / "config"
    home = tmp_path / "home"
    config.mkdir()
    old = make_release(home, "1.9.0")
    new = make_release(home, "2.0.0", "beta")
    (home / "current").symlink_to(old)
    (config / "state.env").write_text(
        f'HEIDI_HOME="{home}"\nHEIDI_VERSION="1.9.0"\nHEIDI_CHANNEL="stable"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HEIDI_CONFIG_DIR", str(config))
    monkeypatch.setattr(module, "service_action", lambda *_args, **_kwargs: None)
    result = module.rollback_command(
        type("Args", (), {"version": "2.0.0", "no_backup": True, "no_verify": True})()
    )
    assert result == 0
    assert (home / "current").resolve() == new.resolve()
    state = module.parse_state(config / "state.env")
    assert state["HEIDI_VERSION"] == "2.0.0"
    assert state["HEIDI_CHANNEL"] == "beta"


def test_rollback_restores_previous_release_and_state_when_verification_fails(tmp_path: Path, monkeypatch):
    module = load_module()
    config = tmp_path / "config"
    home = tmp_path / "home"
    config.mkdir()
    old = make_release(home, "1.9.0")
    new = make_release(home, "2.0.0")
    (new / "source" / "scripts" / "verify-stack.sh").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (new / "source" / "scripts" / "verify-stack.sh").chmod(0o755)
    (home / "current").symlink_to(old)
    original_state = f'HEIDI_HOME="{home}"\nHEIDI_VERSION="1.9.0"\nHEIDI_CHANNEL="stable"\n'
    (config / "state.env").write_text(original_state, encoding="utf-8")
    monkeypatch.setenv("HEIDI_CONFIG_DIR", str(config))
    monkeypatch.setattr(module, "service_action", lambda *_args, **_kwargs: None)
    try:
        module.rollback_command(
            type("Args", (), {"version": "2.0.0", "no_backup": True, "no_verify": False})()
        )
    except Exception:
        pass
    else:
        raise AssertionError("failed verification must abort rollback")
    assert (home / "current").resolve() == old.resolve()
    assert (config / "state.env").read_text(encoding="utf-8") == original_state
