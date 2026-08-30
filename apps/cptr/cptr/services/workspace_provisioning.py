"""Authenticated host-level workspace provisioning for ChatGPT Direct Coding.

The service closes the zero-workspace bootstrap gap without exposing a generic
host shell. Managed workspaces are created below CPTR_WORKSPACE_ROOT; external
imports are register-only and can never be recursively deleted by this API.
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cptr.env import (
    WORKSPACE_CLONE_TIMEOUT_SECONDS,
    WORKSPACE_DELETE_CONFIRM_TTL_SECONDS,
    WORKSPACE_ROOT,
)
from cptr.models import Workspace
from cptr.services.fdx_intelligence import service as fdx_intelligence_service
from cptr.utils.identity import ExecutionIdentity, env_for, expand_user_path, preexec_for


_WORKSPACE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SCP_GIT_URL_RE = re.compile(
    r"^(?P<user>[A-Za-z0-9._-]+)@(?P<host>[A-Za-z0-9.-]+):(?P<path>[^\s]+)$"
)


class WorkspaceProvisioningError(RuntimeError):
    """Structured provisioning failure safe to surface through the Control API."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        retriable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retriable = retriable


class WorkspaceProvisioningService:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        fdx_service: Any = fdx_intelligence_service,
        clock=time.monotonic,
    ) -> None:
        self.workspace_root = (workspace_root or WORKSPACE_ROOT).expanduser().resolve()
        self.fdx_service = fdx_service
        self.clock = clock
        self._delete_confirmations: dict[str, dict[str, Any]] = {}
        self._delete_lock = asyncio.Lock()

    @staticmethod
    def _validate_name(name: str) -> str:
        value = (name or "").strip()
        if value in {"", ".", ".."} or not _WORKSPACE_NAME_RE.fullmatch(value):
            raise WorkspaceProvisioningError(
                "WORKSPACE_INVALID_NAME",
                "workspace name must contain only letters, numbers, dot, underscore, or dash",
            )
        return value

    @staticmethod
    def _validate_repository_url(repository_url: str) -> str:
        value = (repository_url or "").strip()
        if not value or any(char.isspace() for char in value):
            raise WorkspaceProvisioningError(
                "WORKSPACE_INVALID_REPOSITORY_URL", "repository URL is invalid"
            )

        scp = _SCP_GIT_URL_RE.fullmatch(value)
        if scp:
            if not scp.group("path") or scp.group("path").startswith(('/', '\\')):
                raise WorkspaceProvisioningError(
                    "WORKSPACE_INVALID_REPOSITORY_URL", "repository URL is invalid"
                )
            return value

        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "ssh"} or not parsed.hostname:
            raise WorkspaceProvisioningError(
                "WORKSPACE_INVALID_REPOSITORY_URL",
                "repository URL must use HTTPS or SSH",
            )
        # Never accept URL userinfo for HTTPS: it commonly carries tokens or
        # passwords. SSH usernames are conventional, but passwords remain
        # forbidden in all URL forms.
        if parsed.password is not None or (parsed.scheme == "https" and parsed.username is not None):
            raise WorkspaceProvisioningError(
                "WORKSPACE_INVALID_REPOSITORY_URL",
                "repository URLs with embedded credentials are not accepted",
            )
        return value

    @classmethod
    def _name_from_repository_url(cls, repository_url: str) -> str:
        scp = _SCP_GIT_URL_RE.fullmatch(repository_url)
        raw_path = scp.group("path") if scp else urlsplit(repository_url).path
        candidate = Path(raw_path.rstrip("/")).name
        if candidate.endswith(".git"):
            candidate = candidate[:-4]
        return cls._validate_name(candidate)

    def _managed_path(self, name: str) -> Path:
        validated = self._validate_name(name)
        path = (self.workspace_root / validated).resolve()
        if not path.is_relative_to(self.workspace_root):
            raise WorkspaceProvisioningError(
                "WORKSPACE_PATH_ESCAPE", "managed workspace path escapes the workspace root"
            )
        return path

    def _is_managed_path(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(self.workspace_root)
        except (OSError, ValueError):
            return False

    async def _workspace_for_user(self, user_id: str, workspace_id: str) -> Workspace:
        for workspace in await Workspace.get_by_user(user_id):
            if workspace.id == workspace_id:
                return workspace
        raise WorkspaceProvisioningError(
            "WORKSPACE_NOT_FOUND", "workspace not found", status_code=404
        )

    async def _register(
        self,
        *,
        user_id: str,
        path: Path,
        name: str,
        identity: ExecutionIdentity,
        warm_fdx: bool,
    ) -> dict[str, Any]:
        resolved = path.resolve()
        workspace = await Workspace.upsert(user_id, str(resolved), name, {})
        return await self._readiness(
            user_id=user_id,
            workspace=workspace,
            identity=identity,
            warm_fdx=warm_fdx,
        )

    async def _readiness(
        self,
        *,
        user_id: str,
        workspace: Workspace,
        identity: ExecutionIdentity,
        warm_fdx: bool,
    ) -> dict[str, Any]:
        root = Path(workspace.path).resolve()
        available = root.is_dir()
        git_repository = available and (root / ".git").exists()
        fdx: dict[str, Any]
        if git_repository and warm_fdx:
            try:
                value = await self.fdx_service.execute(
                    user_id=user_id,
                    workspace_id=workspace.id,
                    root=root,
                    identity=identity,
                    action="status",
                    options={},
                )
                fdx = value if isinstance(value, dict) else {"status": "degraded"}
            except Exception:
                # FDX is an intelligence accelerator, never the authority that
                # decides whether a CPTR workspace itself is usable.
                fdx = {
                    "status": "unavailable",
                    "fallback_recommended": True,
                    "error_code": "FDX_WARMUP_FAILED",
                }
        elif git_repository:
            fdx = {"status": "skipped", "fallback_recommended": False}
        else:
            fdx = {
                "status": "not_applicable",
                "fallback_recommended": True,
                "reason": "workspace is not a Git repository",
            }
        return {
            "workspace_id": workspace.id,
            "name": workspace.name,
            "available": available,
            "managed": self._is_managed_path(root),
            "git_repository": git_repository,
            "fdx": fdx,
        }

    async def create(
        self,
        *,
        user_id: str,
        identity: ExecutionIdentity,
        name: str,
        warm_fdx: bool = True,
    ) -> dict[str, Any]:
        destination = self._managed_path(name)
        await asyncio.to_thread(self.workspace_root.mkdir, parents=True, exist_ok=True)
        if destination.exists():
            raise WorkspaceProvisioningError(
                "WORKSPACE_ALREADY_EXISTS",
                "managed workspace destination already exists",
                status_code=409,
            )
        await asyncio.to_thread(destination.mkdir, mode=0o700)
        return await self._register(
            user_id=user_id,
            path=destination,
            name=self._validate_name(name),
            identity=identity,
            warm_fdx=warm_fdx,
        )

    async def clone(
        self,
        *,
        user_id: str,
        identity: ExecutionIdentity,
        repository_url: str,
        name: str | None = None,
        warm_fdx: bool = True,
    ) -> dict[str, Any]:
        validated_url = self._validate_repository_url(repository_url)
        workspace_name = self._validate_name(name) if name else self._name_from_repository_url(validated_url)
        destination = self._managed_path(workspace_name)
        await asyncio.to_thread(self.workspace_root.mkdir, parents=True, exist_ok=True)
        if destination.exists():
            raise WorkspaceProvisioningError(
                "WORKSPACE_ALREADY_EXISTS",
                "managed workspace destination already exists",
                status_code=409,
            )

        kwargs: dict[str, Any] = {
            "cwd": str(self.workspace_root),
            "env": env_for(identity, self.workspace_root),
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }
        if os.name != "nt":
            kwargs["start_new_session"] = True
            preexec = preexec_for(identity)
            if preexec is not None:
                kwargs["preexec_fn"] = preexec
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                validated_url,
                str(destination),
                **kwargs,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=WORKSPACE_CLONE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except (UnboundLocalError, ProcessLookupError):
                pass
            await asyncio.to_thread(shutil.rmtree, destination, True)
            raise WorkspaceProvisioningError(
                "WORKSPACE_CLONE_TIMEOUT",
                "Git clone timed out",
                status_code=504,
                retriable=True,
            ) from exc
        except (FileNotFoundError, PermissionError, OSError) as exc:
            await asyncio.to_thread(shutil.rmtree, destination, True)
            raise WorkspaceProvisioningError(
                "WORKSPACE_CLONE_UNAVAILABLE",
                "Git clone could not be started",
                status_code=503,
                retriable=True,
            ) from exc

        if process.returncode != 0:
            await asyncio.to_thread(shutil.rmtree, destination, True)
            detail = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
            # Do not echo the repository URL or arbitrary host paths back to ChatGPT.
            summary = detail.splitlines()[-1][:240] if detail else "Git clone failed"
            raise WorkspaceProvisioningError(
                "WORKSPACE_CLONE_FAILED",
                summary,
                status_code=422,
                retriable=True,
            )
        return await self._register(
            user_id=user_id,
            path=destination,
            name=workspace_name,
            identity=identity,
            warm_fdx=warm_fdx,
        )

    async def import_existing(
        self,
        *,
        user_id: str,
        identity: ExecutionIdentity,
        path: str,
        name: str | None = None,
        warm_fdx: bool = True,
    ) -> dict[str, Any]:
        expanded = expand_user_path(path, identity)
        if not expanded.is_absolute():
            raise WorkspaceProvisioningError(
                "WORKSPACE_IMPORT_PATH_INVALID", "import path must be absolute"
            )
        resolved = expanded.resolve()
        if not resolved.is_dir():
            raise WorkspaceProvisioningError(
                "WORKSPACE_IMPORT_NOT_FOUND", "import directory does not exist", status_code=404
            )
        workspace_name = self._validate_name(name) if name else self._validate_name(resolved.name)
        return await self._register(
            user_id=user_id,
            path=resolved,
            name=workspace_name,
            identity=identity,
            warm_fdx=warm_fdx,
        )

    async def refresh(
        self,
        *,
        user_id: str,
        workspace_id: str,
        identity: ExecutionIdentity,
        warm_fdx: bool = True,
    ) -> dict[str, Any]:
        workspace = await self._workspace_for_user(user_id, workspace_id)
        return await self._readiness(
            user_id=user_id,
            workspace=workspace,
            identity=identity,
            warm_fdx=warm_fdx,
        )

    async def archive(self, *, user_id: str, workspace_id: str) -> dict[str, Any]:
        workspace = await self._workspace_for_user(user_id, workspace_id)
        path = str(Path(workspace.path).resolve())
        await Workspace.delete_by_path(user_id, path)
        return {"workspace_id": workspace_id, "archived": True, "files_deleted": False}

    async def request_delete(self, *, user_id: str, workspace_id: str) -> dict[str, Any]:
        workspace = await self._workspace_for_user(user_id, workspace_id)
        path = Path(workspace.path).resolve()
        if not self._is_managed_path(path):
            raise WorkspaceProvisioningError(
                "WORKSPACE_DELETE_OUTSIDE_MANAGED_ROOT",
                "only managed Heidi workspaces can be recursively deleted",
                status_code=409,
            )
        confirmation_id = f"wsc_{secrets.token_urlsafe(24)}"
        expires_at = self.clock() + WORKSPACE_DELETE_CONFIRM_TTL_SECONDS
        async with self._delete_lock:
            self._delete_confirmations[confirmation_id] = {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "path": str(path),
                "expires_at": expires_at,
            }
        return {
            "workspace_id": workspace_id,
            "confirmation_id": confirmation_id,
            "expires_in_seconds": WORKSPACE_DELETE_CONFIRM_TTL_SECONDS,
        }

    async def confirm_delete(self, *, user_id: str, confirmation_id: str) -> dict[str, Any]:
        async with self._delete_lock:
            pending = self._delete_confirmations.pop(confirmation_id, None)
        if pending is None or pending.get("user_id") != user_id:
            raise WorkspaceProvisioningError(
                "WORKSPACE_DELETE_CONFIRMATION_INVALID",
                "workspace deletion confirmation is invalid",
                status_code=409,
            )
        if float(pending["expires_at"]) < self.clock():
            raise WorkspaceProvisioningError(
                "WORKSPACE_DELETE_CONFIRMATION_EXPIRED",
                "workspace deletion confirmation expired",
                status_code=409,
            )
        path = Path(str(pending["path"])).resolve()
        if not self._is_managed_path(path):
            raise WorkspaceProvisioningError(
                "WORKSPACE_DELETE_OUTSIDE_MANAGED_ROOT",
                "only managed Heidi workspaces can be recursively deleted",
                status_code=409,
            )
        if path.exists():
            await asyncio.to_thread(shutil.rmtree, path)
        await Workspace.delete_by_path(user_id, str(path))
        return {
            "workspace_id": str(pending["workspace_id"]),
            "archived": True,
            "files_deleted": True,
        }


service = WorkspaceProvisioningService()
