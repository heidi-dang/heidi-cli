from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cptr.routers.control import list_workspaces
from cptr.routers.workspace_lifecycle import WorkspaceLifecycleRequest, workspace_lifecycle
from cptr.services.workspace_provisioning import WorkspaceProvisioningService
from cptr.utils.identity import ExecutionIdentity


IDENTITY = ExecutionIdentity(
    app_user_id="user_1",
    username="tester",
    uid=None,
    gid=None,
    groups=(),
    home="/tmp/tester",
    shell="/bin/sh",
    is_pam=False,
)


@pytest.mark.asyncio
async def test_zero_workspace_clone_registers_workspace_and_warms_fdx_without_network(tmp_path: Path):
    """Acceptance path: empty registry -> clone -> FDX readiness -> discoverable workspace.

    The production URL validator still sees an HTTPS repository. The subprocess
    boundary is replaced with a deterministic local Git clone so CI never needs
    external network access while still verifying the exact argv passed by CPTR.
    """
    source = tmp_path / "source"
    subprocess.run(["git", "init", str(source)], check=True, capture_output=True)

    managed_root = tmp_path / "managed"
    fdx = SimpleNamespace(
        warm_repository=AsyncMock(return_value={"status": "ok", "provider": "fdx_native"})
    )
    service = WorkspaceProvisioningService(workspace_root=managed_root, fdx_service=fdx)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    rows: list[SimpleNamespace] = []

    async def upsert(user_id: str, path: str, name: str, data: dict):
        row = SimpleNamespace(
            id="ws_bootstrap",
            user_id=user_id,
            path=path,
            name=name,
            data=data,
            created_at=1,
            updated_at=2,
        )
        rows[:] = [row]
        return row

    class Proc:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def spawn(*argv, **kwargs):
        assert argv[:3] == ("git", "clone", "https://example.invalid/bootstrap.git")
        destination = Path(argv[-1])
        assert destination == managed_root / "bootstrap"
        assert kwargs["cwd"] == str(managed_root)
        subprocess.run(
            ["git", "clone", str(source), str(destination)],
            check=True,
            capture_output=True,
        )
        return Proc()

    with (
        patch("cptr.routers.control._user", new=AsyncMock(return_value="user_1")),
        patch("cptr.routers.control.Workspace.get_by_user", new=AsyncMock(return_value=[])),
    ):
        assert await list_workspaces(request) == {"workspaces": []}

    with (
        patch("cptr.routers.workspace_lifecycle._user", new=AsyncMock(return_value="user_1")),
        patch("cptr.routers.workspace_lifecycle.identity_for_request", new=AsyncMock(return_value=IDENTITY)),
        patch("cptr.routers.workspace_lifecycle.workspace_provisioning_service", service),
        patch(
            "cptr.services.workspace_provisioning.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=spawn),
        ) as create_process,
        patch("cptr.services.workspace_provisioning.Workspace.upsert", new=AsyncMock(side_effect=upsert)),
    ):
        created = await workspace_lifecycle(
            request,
            WorkspaceLifecycleRequest(
                action="clone",
                repository_url="https://example.invalid/bootstrap.git",
            ),
        )

    assert create_process.await_args.args[:3] == (
        "git",
        "clone",
        "https://example.invalid/bootstrap.git",
    )
    assert created == {
        "workspace_id": "ws_bootstrap",
        "name": "bootstrap",
        "available": True,
        "managed": True,
        "git_repository": True,
        "fdx": {"status": "ok", "provider": "fdx_native"},
    }
    assert "path" not in created
    assert (managed_root / "bootstrap" / ".git").is_dir()
    fdx.warm_repository.assert_awaited_once()

    with (
        patch("cptr.routers.control._user", new=AsyncMock(return_value="user_1")),
        patch("cptr.routers.control.Workspace.get_by_user", new=AsyncMock(return_value=rows)),
    ):
        discovered = await list_workspaces(request)

    assert discovered["workspaces"] == [
        {
            "workspace_id": "ws_bootstrap",
            "name": "bootstrap",
            "available": True,
            "last_used_at": 2,
        }
    ]
