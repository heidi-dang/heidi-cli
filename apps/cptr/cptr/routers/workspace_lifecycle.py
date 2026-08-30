"""Workspace bootstrap and lifecycle endpoints for the CPTR Control API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from cptr.services.control_auth import authenticate_control_request
from cptr.services.workspace_provisioning import (
    WorkspaceProvisioningError,
    service as workspace_provisioning_service,
)
from cptr.utils.identity import IdentityUnavailable, identity_for_request


router = APIRouter(prefix="/workspaces", tags=["control-workspaces"])


class WorkspaceLifecycleRequest(BaseModel):
    action: Literal[
        "create",
        "clone",
        "import",
        "refresh",
        "archive",
        "request_delete",
        "confirm_delete",
    ]
    workspace_id: str | None = Field(default=None, min_length=1, max_length=200)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    repository_url: str | None = Field(default=None, min_length=1, max_length=4_096)
    path: str | None = Field(default=None, min_length=1, max_length=1_000)
    confirmation_id: str | None = Field(default=None, min_length=1, max_length=200)
    warm_fdx: bool = True


def _required(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "WORKSPACE_LIFECYCLE_FIELD_REQUIRED",
                "message": f"{field} is required for this action",
                "retriable": False,
                "field": field,
            },
        )
    return value.strip()


async def _user(request: Request, scope: str) -> str:
    try:
        return await authenticate_control_request(request, scope)
    except PermissionError as exc:
        if str(exc).startswith("missing required scope"):
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        raise HTTPException(status_code=401, detail="control-plane authentication failed") from exc


def _raise_provisioning(exc: WorkspaceProvisioningError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "code": exc.code,
            "message": str(exc),
            "retriable": exc.retriable,
        },
    ) from exc


@router.post("/lifecycle")
async def workspace_lifecycle(request: Request, body: WorkspaceLifecycleRequest):
    delete_action = body.action in {"request_delete", "confirm_delete"}
    user_id = await _user(request, "workspace:delete" if delete_action else "workspace:provision")

    try:
        if body.action == "request_delete":
            return await workspace_provisioning_service.request_delete(
                user_id=user_id,
                workspace_id=_required(body.workspace_id, "workspace_id"),
            )
        if body.action == "confirm_delete":
            return await workspace_provisioning_service.confirm_delete(
                user_id=user_id,
                confirmation_id=_required(body.confirmation_id, "confirmation_id"),
            )
        if body.action == "archive":
            return await workspace_provisioning_service.archive(
                user_id=user_id,
                workspace_id=_required(body.workspace_id, "workspace_id"),
            )

        identity = await identity_for_request(request)
        if body.action == "create":
            return await workspace_provisioning_service.create(
                user_id=user_id,
                identity=identity,
                name=_required(body.name, "name"),
                warm_fdx=body.warm_fdx,
            )
        if body.action == "clone":
            return await workspace_provisioning_service.clone(
                user_id=user_id,
                identity=identity,
                repository_url=_required(body.repository_url, "repository_url"),
                name=body.name.strip() if body.name else None,
                warm_fdx=body.warm_fdx,
            )
        if body.action == "import":
            return await workspace_provisioning_service.import_existing(
                user_id=user_id,
                identity=identity,
                path=_required(body.path, "path"),
                name=body.name.strip() if body.name else None,
                warm_fdx=body.warm_fdx,
            )
        return await workspace_provisioning_service.refresh(
            user_id=user_id,
            workspace_id=_required(body.workspace_id, "workspace_id"),
            identity=identity,
            warm_fdx=body.warm_fdx,
        )
    except IdentityUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except WorkspaceProvisioningError as exc:
        _raise_provisioning(exc)
        raise AssertionError("unreachable")
