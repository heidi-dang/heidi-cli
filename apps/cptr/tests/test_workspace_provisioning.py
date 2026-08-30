from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cptr.services.workspace_provisioning import (
    WorkspaceProvisioningError,
    WorkspaceProvisioningService,
)
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


class FakeFdx:
    def __init__(self, result: dict | None = None):
        self.result = result or {"status": "ok", "provider": "fdx_native"}
        self.execute = AsyncMock(return_value=self.result)


def workspace_row(path: Path, *, workspace_id: str = "ws_1", name: str = "repo"):
    return SimpleNamespace(id=workspace_id, user_id="user_1", path=str(path), name=name, data={})


@pytest.mark.asyncio
async def test_create_registers_managed_workspace_without_exposing_host_path(tmp_path: Path):
    root = tmp_path / "managed"
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=FakeFdx())
    row = workspace_row(root / "alpha", name="alpha")

    with patch("cptr.services.workspace_provisioning.Workspace.upsert", new=AsyncMock(return_value=row)) as upsert:
        result = await service.create(user_id="user_1", identity=IDENTITY, name="alpha")

    assert (root / "alpha").is_dir()
    upsert.assert_awaited_once()
    assert result["workspace_id"] == "ws_1"
    assert result["name"] == "alpha"
    assert result["managed"] is True
    assert result["available"] is True
    assert "path" not in result


@pytest.mark.asyncio
async def test_clone_uses_argv_subprocess_and_warms_fdx_for_git_repo(tmp_path: Path):
    root = tmp_path / "managed"
    fdx = FakeFdx()
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=fdx)
    row = workspace_row(root / "heidi-cli", name="heidi-cli")

    class Proc:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def spawn(*argv, **kwargs):
        destination = Path(argv[-1])
        destination.mkdir(parents=True)
        (destination / ".git").mkdir()
        assert kwargs.get("cwd") == str(root)
        return Proc()

    with (
        patch("cptr.services.workspace_provisioning.asyncio.create_subprocess_exec", new=AsyncMock(side_effect=spawn)) as create_process,
        patch("cptr.services.workspace_provisioning.Workspace.upsert", new=AsyncMock(return_value=row)),
    ):
        result = await service.clone(
            user_id="user_1",
            identity=IDENTITY,
            repository_url="https://github.com/heidi-dang/heidi-cli.git",
        )

    argv = create_process.await_args.args
    assert argv[0:2] == ("git", "clone")
    assert argv[2] == "https://github.com/heidi-dang/heidi-cli.git"
    assert argv[-1] == str(root / "heidi-cli")
    assert result["git_repository"] is True
    assert result["fdx"]["status"] == "ok"
    fdx.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "repository_url",
    [
        "https://user:secret@example.com/org/repo.git",
        "https://token@example.com/org/repo.git",
        "file:///etc",
        "ftp://example.com/repo.git",
    ],
)
async def test_clone_rejects_credential_bearing_or_unsupported_repository_urls(
    tmp_path: Path, repository_url: str
):
    service = WorkspaceProvisioningService(workspace_root=tmp_path / "managed", fdx_service=FakeFdx())

    with pytest.raises(WorkspaceProvisioningError) as rejected:
        await service.clone(user_id="user_1", identity=IDENTITY, repository_url=repository_url)

    assert rejected.value.code == "WORKSPACE_INVALID_REPOSITORY_URL"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["../escape", "bad/name", "", ".", ".."])
async def test_managed_workspace_name_cannot_escape_root(tmp_path: Path, name: str):
    service = WorkspaceProvisioningService(workspace_root=tmp_path / "managed", fdx_service=FakeFdx())

    with pytest.raises(WorkspaceProvisioningError) as rejected:
        await service.create(user_id="user_1", identity=IDENTITY, name=name)

    assert rejected.value.code == "WORKSPACE_INVALID_NAME"


@pytest.mark.asyncio
async def test_import_registers_existing_directory_but_marks_it_unmanaged(tmp_path: Path):
    external = tmp_path / "external"
    external.mkdir()
    row = workspace_row(external, name="external")
    service = WorkspaceProvisioningService(workspace_root=tmp_path / "managed", fdx_service=FakeFdx())

    with patch("cptr.services.workspace_provisioning.Workspace.upsert", new=AsyncMock(return_value=row)):
        result = await service.import_existing(
            user_id="user_1", identity=IDENTITY, path=str(external), name="external"
        )

    assert result["workspace_id"] == "ws_1"
    assert result["managed"] is False
    assert "path" not in result


@pytest.mark.asyncio
async def test_fdx_unavailable_is_non_fatal_readiness_metadata(tmp_path: Path):
    root = tmp_path / "managed"
    repo = root / "repo"
    (repo / ".git").mkdir(parents=True)
    fdx = FakeFdx({
        "status": "unavailable",
        "provider": "fdx_native",
        "fallback_recommended": True,
        "error_code": "FDX_BINARY_UNAVAILABLE",
    })
    row = workspace_row(repo)
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=fdx)

    with patch("cptr.services.workspace_provisioning.Workspace.upsert", new=AsyncMock(return_value=row)):
        result = await service.import_existing(user_id="user_1", identity=IDENTITY, path=str(repo))

    assert result["available"] is True
    assert result["git_repository"] is True
    assert result["fdx"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_archive_unregisters_workspace_without_deleting_files(tmp_path: Path):
    root = tmp_path / "managed"
    repo = root / "repo"
    repo.mkdir(parents=True)
    row = workspace_row(repo)
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=FakeFdx())

    with (
        patch("cptr.services.workspace_provisioning.Workspace.get_by_user", new=AsyncMock(return_value=[row])),
        patch("cptr.services.workspace_provisioning.Workspace.delete_by_path", new=AsyncMock(return_value=True)) as delete_row,
    ):
        result = await service.archive(user_id="user_1", workspace_id="ws_1")

    assert repo.exists()
    delete_row.assert_awaited_once_with("user_1", str(repo.resolve()))
    assert result == {"workspace_id": "ws_1", "archived": True, "files_deleted": False}


@pytest.mark.asyncio
async def test_confirm_delete_removes_only_managed_workspace_after_matching_confirmation(tmp_path: Path):
    root = tmp_path / "managed"
    repo = root / "repo"
    (repo / ".git").mkdir(parents=True)
    row = workspace_row(repo)
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=FakeFdx())

    with (
        patch("cptr.services.workspace_provisioning.Workspace.get_by_user", new=AsyncMock(return_value=[row])),
        patch("cptr.services.workspace_provisioning.Workspace.delete_by_path", new=AsyncMock(return_value=True)) as delete_row,
    ):
        pending = await service.request_delete(user_id="user_1", workspace_id="ws_1")
        result = await service.confirm_delete(
            user_id="user_1", confirmation_id=pending["confirmation_id"]
        )

    assert not repo.exists()
    delete_row.assert_awaited_once_with("user_1", str(repo.resolve()))
    assert result == {"workspace_id": "ws_1", "archived": True, "files_deleted": True}


@pytest.mark.asyncio
async def test_delete_refuses_imported_workspace_outside_managed_root(tmp_path: Path):
    root = tmp_path / "managed"
    external = tmp_path / "external"
    external.mkdir()
    row = workspace_row(external)
    service = WorkspaceProvisioningService(workspace_root=root, fdx_service=FakeFdx())

    with patch("cptr.services.workspace_provisioning.Workspace.get_by_user", new=AsyncMock(return_value=[row])):
        with pytest.raises(WorkspaceProvisioningError) as rejected:
            await service.request_delete(user_id="user_1", workspace_id="ws_1")

    assert rejected.value.code == "WORKSPACE_DELETE_OUTSIDE_MANAGED_ROOT"
    assert external.exists()
