from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cptr.routers.workspace_lifecycle import WorkspaceLifecycleRequest, workspace_lifecycle
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


def request():
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()), state=SimpleNamespace())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "payload", "method"),
    [
        ("create", {"name": "alpha"}, "create"),
        ("clone", {"repository_url": "https://github.com/heidi-dang/heidi-cli.git"}, "clone"),
        ("import", {"path": "/tmp/existing"}, "import_existing"),
        ("refresh", {"workspace_id": "ws_1"}, "refresh"),
        ("archive", {"workspace_id": "ws_1"}, "archive"),
    ],
)
async def test_non_delete_workspace_lifecycle_actions_require_provision_scope(
    action: str, payload: dict, method: str
):
    req = request()
    service = SimpleNamespace(**{method: AsyncMock(return_value={"workspace_id": "ws_1"})})
    body = WorkspaceLifecycleRequest(action=action, **payload)

    with (
        patch("cptr.routers.workspace_lifecycle._user", new=AsyncMock(return_value="user_1")) as user,
        patch(
            "cptr.routers.workspace_lifecycle.identity_for_request",
            new=AsyncMock(return_value=IDENTITY),
        ),
        patch("cptr.routers.workspace_lifecycle.workspace_provisioning_service", service),
    ):
        result = await workspace_lifecycle(req, body)

    assert result["workspace_id"] == "ws_1"
    user.assert_awaited_once_with(req, "workspace:provision")
    getattr(service, method).assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "payload", "method"),
    [
        ("request_delete", {"workspace_id": "ws_1"}, "request_delete"),
        ("confirm_delete", {"confirmation_id": "confirm_1"}, "confirm_delete"),
    ],
)
async def test_delete_workspace_lifecycle_actions_require_delete_scope(
    action: str, payload: dict, method: str
):
    req = request()
    service = SimpleNamespace(**{method: AsyncMock(return_value={"workspace_id": "ws_1"})})
    body = WorkspaceLifecycleRequest(action=action, **payload)

    with (
        patch("cptr.routers.workspace_lifecycle._user", new=AsyncMock(return_value="user_1")) as user,
        patch("cptr.routers.workspace_lifecycle.workspace_provisioning_service", service),
    ):
        result = await workspace_lifecycle(req, body)

    assert result["workspace_id"] == "ws_1"
    user.assert_awaited_once_with(req, "workspace:delete")
    getattr(service, method).assert_awaited_once()


@pytest.mark.asyncio
async def test_clone_forwards_identity_url_name_and_fdx_preference():
    req = request()
    clone = AsyncMock(return_value={"workspace_id": "ws_clone"})
    service = SimpleNamespace(clone=clone)
    body = WorkspaceLifecycleRequest(
        action="clone",
        repository_url="https://github.com/heidi-dang/heidi-cli.git",
        name="heidi",
        warm_fdx=False,
    )

    with (
        patch("cptr.routers.workspace_lifecycle._user", new=AsyncMock(return_value="user_1")),
        patch(
            "cptr.routers.workspace_lifecycle.identity_for_request",
            new=AsyncMock(return_value=IDENTITY),
        ),
        patch("cptr.routers.workspace_lifecycle.workspace_provisioning_service", service),
    ):
        await workspace_lifecycle(req, body)

    clone.assert_awaited_once_with(
        user_id="user_1",
        identity=IDENTITY,
        repository_url="https://github.com/heidi-dang/heidi-cli.git",
        name="heidi",
        warm_fdx=False,
    )
