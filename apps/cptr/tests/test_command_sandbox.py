from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cptr.routers.coding import _command_context
from cptr.services.command_sandbox import SandboxUnavailable, configured_profile, sandbox_command


def test_direct_coding_command_context_marks_sandbox_and_network_policy():
    request = SimpleNamespace()
    context = _command_context(
        request=request,
        user_id="user_1",
        workspace_id="ws_1",
        workspace_path="/tmp/workspace",
        worker_id="worker_1",
        allow_network=True,
    )
    assert context["direct_coding"] is True
    assert context["allow_network"] is True
    assert context["direct_worker_id"] == "worker_1"


def test_bubblewrap_denies_network_and_writes_only_workspace(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    work_dir = workspace / "src"
    work_dir.mkdir()
    with patch("cptr.services.command_sandbox.shutil.which", return_value="/usr/bin/bwrap"):
        wrapped = sandbox_command(
            command="printf hello",
            argv=None,
            workspace=workspace,
            work_dir=work_dir,
            allow_network=False,
            profile="bubblewrap",
        )
    assert wrapped.profile == "bubblewrap"
    assert wrapped.shell_command is None
    assert wrapped.argv is not None
    assert "--unshare-net" in wrapped.argv
    assert ["--bind", str(workspace.resolve()), str(workspace.resolve())] == wrapped.argv[
        wrapped.argv.index("--bind") : wrapped.argv.index("--bind") + 3
    ]
    assert wrapped.argv[-4:] == ["--", "/bin/sh", "-lc", "printf hello"]


def test_default_direct_coding_sandbox_is_fail_closed_bubblewrap(monkeypatch):
    monkeypatch.delenv("CPTR_DIRECT_CODING_SANDBOX", raising=False)
    assert configured_profile() == "bubblewrap"


def test_explicit_unavailable_sandbox_fails_closed(tmp_path: Path):
    with patch("cptr.services.command_sandbox.shutil.which", return_value=None):
        with pytest.raises(SandboxUnavailable, match="bubblewrap"):
            sandbox_command(
                command="true",
                argv=None,
                workspace=tmp_path,
                work_dir=tmp_path,
                allow_network=False,
                profile="bubblewrap",
            )
