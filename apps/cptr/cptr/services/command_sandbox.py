"""Direct Coding process-isolation profiles.

The sandbox is intentionally applied only to ChatGPT Direct Coding/test commands.
Interactive legacy terminals and delegated-agent execution keep their existing
runtime unless they explicitly opt into the same profile.
"""

from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path


class SandboxUnavailable(RuntimeError):
    """Raised when an explicitly selected isolation profile cannot run."""


@dataclass(frozen=True)
class SandboxCommand:
    argv: list[str] | None
    shell_command: str | None
    profile: str


_ALLOWED = {"host", "auto", "bubblewrap", "systemd", "container", "vm"}


def configured_profile() -> str:
    value = os.getenv("CPTR_DIRECT_CODING_SANDBOX", "bubblewrap").strip().lower() or "bubblewrap"
    if value not in _ALLOWED:
        raise SandboxUnavailable(
            f"unsupported CPTR_DIRECT_CODING_SANDBOX={value!r}; expected one of {sorted(_ALLOWED)}"
        )
    if value == "auto":
        if shutil.which("bwrap"):
            return "bubblewrap"
        if shutil.which("systemd-run"):
            return "systemd"
        return "host"
    return value


def _original_argv(command: str, argv: list[str] | None) -> list[str]:
    return list(argv) if argv is not None else ["/bin/sh", "-lc", command]


def _bubblewrap(
    *, command: str, argv: list[str] | None, workspace: Path, work_dir: Path, allow_network: bool
) -> SandboxCommand:
    binary = shutil.which("bwrap")
    if not binary:
        raise SandboxUnavailable(
            "bubblewrap sandbox requested but bwrap is not installed; install bubblewrap or choose host/systemd"
        )
    workspace = workspace.resolve()
    work_dir = work_dir.resolve()
    if not work_dir.is_relative_to(workspace):
        raise SandboxUnavailable("sandbox working directory must remain inside the workspace")
    wrapped = [
        binary,
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--ro-bind",
        "/",
        "/",
        "--dev-bind",
        "/dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(workspace),
        str(workspace),
        "--chdir",
        str(work_dir),
    ]
    if not allow_network:
        wrapped.append("--unshare-net")
    wrapped.extend(["--", *_original_argv(command, argv)])
    return SandboxCommand(argv=wrapped, shell_command=None, profile="bubblewrap")


def _systemd(
    *, command: str, argv: list[str] | None, work_dir: Path, allow_network: bool
) -> SandboxCommand:
    binary = shutil.which("systemd-run")
    if not binary:
        raise SandboxUnavailable("systemd sandbox requested but systemd-run is not installed")
    wrapped = [
        binary,
        "--user",
        "--scope",
        "--quiet",
        "--pipe",
        "--wait",
        "--collect",
        "--property=NoNewPrivileges=yes",
        "--property=PrivateTmp=yes",
        "--property=TasksMax=1024",
        f"--working-directory={work_dir}",
    ]
    if not allow_network:
        # IPAddressDeny is best-effort on transient user scopes. Managed Heidi
        # deployments prefer bubblewrap when hard network isolation is required.
        wrapped.append("--property=IPAddressDeny=any")
    wrapped.extend(["--", *_original_argv(command, argv)])
    return SandboxCommand(argv=wrapped, shell_command=None, profile="systemd")


def _container(
    *, command: str, argv: list[str] | None, workspace: Path, work_dir: Path, allow_network: bool
) -> SandboxCommand:
    podman = shutil.which("podman")
    if not podman:
        raise SandboxUnavailable("container sandbox requested but podman is not installed")
    image = os.getenv("CPTR_DIRECT_CODING_CONTAINER_IMAGE", "").strip()
    if not image:
        raise SandboxUnavailable(
            "container sandbox requires CPTR_DIRECT_CODING_CONTAINER_IMAGE to name a trusted development image"
        )
    workspace = workspace.resolve()
    relative = work_dir.resolve().relative_to(workspace)
    container_cwd = Path("/workspace") / relative
    wrapped = [
        podman,
        "run",
        "--rm",
        "--read-only",
        "--security-opt=no-new-privileges",
        "--cap-drop=all",
        "--pids-limit=1024",
        "--tmpfs=/tmp:rw,nosuid,nodev,size=1g",
        f"--volume={workspace}:/workspace:rw,Z",
        f"--workdir={container_cwd}",
        "--network=host" if allow_network else "--network=none",
        image,
        *_original_argv(command, argv),
    ]
    return SandboxCommand(argv=wrapped, shell_command=None, profile="container")


def _vm(
    *, command: str, argv: list[str] | None, workspace: Path, work_dir: Path, allow_network: bool
) -> SandboxCommand:
    runner = os.getenv("CPTR_DIRECT_CODING_VM_RUNNER", "").strip()
    if not runner:
        raise SandboxUnavailable(
            "VM sandbox requires CPTR_DIRECT_CODING_VM_RUNNER; configure a trusted runner that accepts the documented argv"
        )
    runner_argv = shlex.split(runner)
    if not runner_argv or not shutil.which(runner_argv[0]):
        raise SandboxUnavailable("configured CPTR_DIRECT_CODING_VM_RUNNER is not executable")
    wrapped = [
        *runner_argv,
        "--workspace",
        str(workspace.resolve()),
        "--cwd",
        str(work_dir.resolve()),
        "--network",
        "allow" if allow_network else "deny",
        "--",
        *_original_argv(command, argv),
    ]
    return SandboxCommand(argv=wrapped, shell_command=None, profile="vm")


def sandbox_command(
    *,
    command: str,
    argv: list[str] | None,
    workspace: str | Path,
    work_dir: str | Path,
    allow_network: bool,
    profile: str | None = None,
) -> SandboxCommand:
    selected = (profile or configured_profile()).strip().lower()
    workspace_path = Path(workspace).resolve()
    work_dir_path = Path(work_dir).resolve()
    if selected == "host":
        return SandboxCommand(argv=argv, shell_command=None if argv is not None else command, profile="host")
    if selected == "bubblewrap":
        return _bubblewrap(
            command=command,
            argv=argv,
            workspace=workspace_path,
            work_dir=work_dir_path,
            allow_network=allow_network,
        )
    if selected == "systemd":
        return _systemd(command=command, argv=argv, work_dir=work_dir_path, allow_network=allow_network)
    if selected == "container":
        return _container(
            command=command,
            argv=argv,
            workspace=workspace_path,
            work_dir=work_dir_path,
            allow_network=allow_network,
        )
    if selected == "vm":
        return _vm(
            command=command,
            argv=argv,
            workspace=workspace_path,
            work_dir=work_dir_path,
            allow_network=allow_network,
        )
    raise SandboxUnavailable(f"unsupported sandbox profile: {selected}")
