#!/usr/bin/env python3
"""Heidi release lifecycle: encrypted backup/restore, rollback, diagnostics.

This module intentionally uses only the Python standard library. External
programs (age, age-keygen, systemctl, curl) are invoked without shell=True.
Secret values are never included in diagnostics output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(?i)(token|secret|password|passwd|authorization|cookie|api[_-]?key|credential|private[_-]?key)"
)
TOKEN_PATTERNS = [
    (re.compile(r"\bsk-cptr-[A-Za-z0-9_-]+\b"), "<redacted-cptr-token>"),
    (re.compile(r"(?i)Bearer\s+\S+"), "Bearer <redacted>"),
    (re.compile(r"\bheidi-mcp-[A-Za-z0-9_-]+\b"), "<redacted-mcp-token>"),
]


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_state(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                result[key] = str(json.loads(value))
                continue
            except json.JSONDecodeError:
                pass
        result[key] = value
    return result


def redact_string(value: str) -> str:
    output = value
    for pattern, replacement in TOKEN_PATTERNS:
        output = pattern.sub(replacement, output)
    return output


def redact_mapping(value: Any, key: str = "") -> Any:
    if key and SENSITIVE_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact_mapping(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_string(value)
    return value


def validate_tar_members(handle: tarfile.TarFile) -> None:
    for member in handle.getmembers():
        name = PurePosixPath(member.name)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError(f"unsafe backup archive member: {member.name}")
        if member.issym() or member.islnk() or member.isdev():
            raise ValueError(f"unsafe backup archive member type: {member.name}")


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"required command is not installed: {name}")
    return path


def run(argv: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def config_dir() -> Path:
    return Path(
        os.environ.get(
            "HEIDI_CONFIG_DIR",
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "heidi-cli",
        )
    ).expanduser()


def state_file() -> Path:
    return config_dir() / "state.env"


def state_or_fail() -> dict[str, str]:
    state = parse_state(state_file())
    if not state:
        raise RuntimeError(f"Heidi state is unavailable: {state_file()}")
    return state


def write_state(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.next")
    payload = "".join(
        f"{key}={json.dumps(str(value), ensure_ascii=False)}\n"
        for key, value in sorted(values.items())
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
    )
    temporary.write_text(payload, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def age_identity_paths() -> tuple[Path, Path]:
    root = config_dir()
    return root / "backup.agekey", root / "backup.recipient"


def ensure_age_identity() -> tuple[Path, str]:
    require_command("age")
    age_keygen = require_command("age-keygen")
    identity, recipient_file = age_identity_paths()
    identity.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(identity.parent, 0o700)
    if not identity.exists():
        subprocess.run([age_keygen, "-o", str(identity)], check=True)
        os.chmod(identity, 0o600)
    recipient = run([age_keygen, "-y", str(identity)]).stdout.strip()
    if not recipient.startswith("age1"):
        raise RuntimeError("age recipient derivation failed")
    recipient_file.write_text(recipient + "\n", encoding="utf-8")
    os.chmod(recipient_file, 0o600)
    return identity, recipient


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_command(args: argparse.Namespace) -> int:
    state = state_or_fail()
    data_dir = Path(state.get("HEIDI_CPTR_DATA_DIR", str(Path.home() / ".cptr"))).expanduser().resolve()
    if not data_dir.is_dir():
        raise RuntimeError(f"CPTR data directory does not exist: {data_dir}")
    _, recipient = ensure_age_identity()
    backup_dir = Path(args.output_dir or state.get("HEIDI_BACKUP_DIR", config_dir() / "backups")).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    version = state.get("HEIDI_VERSION", "unknown")
    output = backup_dir / f"heidi-cptr-{version}-{now_tag()}.tar.age"
    tar_bin = require_command("tar")
    age_bin = require_command("age")
    tar_proc = subprocess.Popen(
        [tar_bin, "-C", str(data_dir.parent), "-cf", "-", data_dir.name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert tar_proc.stdout is not None
    age_proc = subprocess.run(
        [age_bin, "-r", recipient, "-o", str(output)],
        stdin=tar_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tar_proc.stdout.close()
    tar_stderr = tar_proc.stderr.read().decode(errors="replace") if tar_proc.stderr else ""
    tar_code = tar_proc.wait()
    if tar_code != 0 or age_proc.returncode != 0:
        output.unlink(missing_ok=True)
        raise RuntimeError(
            f"encrypted backup failed: tar={tar_code} age={age_proc.returncode} "
            f"{redact_string(tar_stderr)} {redact_string(age_proc.stderr.decode(errors='replace'))}"
        )
    os.chmod(output, 0o600)
    checksum = sha256_file(output)
    checksum_file = output.with_suffix(output.suffix + ".sha256")
    checksum_file.write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    os.chmod(checksum_file, 0o600)
    print(f"Encrypted backup: {output}")
    print(f"SHA-256: {checksum}")
    return 0


def service_scope(state: dict[str, str]) -> list[str]:
    return ["systemctl"] if state.get("HEIDI_SERVICE_SCOPE") == "system" else ["systemctl", "--user"]


def service_action(state: dict[str, str], action: str) -> None:
    base = service_scope(state)
    units = [value for value in state.get("HEIDI_SERVICE_UNITS", "heidi-cptr.service heidi-mcp.service").split() if value]
    for unit in units:
        subprocess.run([*base, action, unit], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restore_command(args: argparse.Namespace) -> int:
    state = state_or_fail()
    encrypted = Path(args.archive).expanduser().resolve()
    if not encrypted.is_file():
        raise RuntimeError(f"backup archive not found: {encrypted}")
    checksum_file = encrypted.with_suffix(encrypted.suffix + ".sha256")
    if checksum_file.exists():
        expected = checksum_file.read_text(encoding="utf-8").split()[0]
        actual = sha256_file(encrypted)
        if expected != actual:
            raise RuntimeError("encrypted backup checksum mismatch")
    identity, _ = ensure_age_identity()
    age_bin = require_command("age")
    data_dir = Path(state.get("HEIDI_CPTR_DATA_DIR", str(Path.home() / ".cptr"))).expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="heidi-restore-", dir=str(data_dir.parent)) as temporary:
        temp = Path(temporary)
        tar_path = temp / "backup.tar"
        with tar_path.open("wb") as output:
            proc = subprocess.run(
                [age_bin, "-d", "-i", str(identity), str(encrypted)],
                stdout=output,
                stderr=subprocess.PIPE,
            )
        if proc.returncode != 0:
            raise RuntimeError("backup decryption failed")
        with tarfile.open(tar_path, "r") as handle:
            validate_tar_members(handle)
            extract_root = temp / "extract"
            extract_root.mkdir()
            handle.extractall(extract_root, filter="data")
        restored = extract_root / data_dir.name
        if not restored.is_dir():
            raise RuntimeError(f"backup does not contain expected data root: {data_dir.name}")
        if not args.no_pre_backup and data_dir.exists():
            backup_command(argparse.Namespace(output_dir=None))
        service_action(state, "stop")
        previous = data_dir.parent / f".{data_dir.name}.pre-restore-{now_tag()}"
        try:
            if data_dir.exists():
                os.replace(data_dir, previous)
            shutil.copytree(restored, data_dir)
            os.chmod(data_dir, 0o700)
        except Exception:
            if previous.exists() and not data_dir.exists():
                os.replace(previous, data_dir)
            raise
        finally:
            service_action(state, "start")
    print(f"Restored CPTR data from: {encrypted}")
    return 0


def atomic_symlink(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary = link.with_name(f".{link.name}.{os.getpid()}.next")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def rollback_command(args: argparse.Namespace) -> int:
    state = state_or_fail()
    state_path = state_file()
    original_state = state_path.read_bytes()
    home = Path(state.get("HEIDI_HOME", Path.home() / ".local/share/heidi-cli")).expanduser().resolve()
    current = home / "current"
    previous = current.resolve() if current.exists() else None
    target = (home / "releases" / args.version).resolve()
    compatibility_path = target / "source" / "release" / "compatibility.json"
    if not compatibility_path.is_file():
        raise RuntimeError(f"installed Heidi release not found or incomplete: {args.version}")
    compatibility = load_json(compatibility_path)
    target_version = str(compatibility.get("heidi_version") or "")
    if target_version != args.version:
        raise RuntimeError(
            f"installed release compatibility version {target_version!r} does not match requested {args.version!r}"
        )
    release_manifest_path = target / "heidi-release.json"
    release_manifest = load_json(release_manifest_path) if release_manifest_path.is_file() else {}
    target_channel = str(release_manifest.get("channel") or state.get("HEIDI_CHANNEL") or "stable")
    if not args.no_backup:
        backup_command(argparse.Namespace(output_dir=None))

    next_state = dict(state)
    next_state.update(
        {
            "HEIDI_VERSION": target_version,
            "HEIDI_CHANNEL": target_channel,
            "HEIDI_RELEASE_DIR": str(current),
            "HEIDI_REPO_DIR": str(current / "source"),
            "HEIDI_VENV_DIR": str(current / "venv"),
        }
    )
    if state.get("HEIDI_FDX_BINARY"):
        next_state["HEIDI_FDX_BINARY"] = str(current / "bin" / "fdx")

    try:
        atomic_symlink(target, current)
        write_state(state_path, next_state)
        service_action(next_state, "restart")
        verify = target / "source" / "scripts" / "verify-stack.sh"
        if verify.is_file() and not args.no_verify:
            subprocess.run(
                [str(verify)],
                check=True,
                env={**os.environ, "HEIDI_CONFIG_DIR": str(config_dir())},
            )
    except Exception as exc:
        if previous is not None:
            atomic_symlink(previous, current)
        state_path.write_bytes(original_state)
        os.chmod(state_path, 0o600)
        service_action(state, "restart")
        raise RuntimeError(f"rollback activation failed and previous release was restored: {exc}") from exc

    print(f"Heidi rollback activated: {args.version}")
    return 0


def command_output(argv: list[str], limit: int = 12000) -> dict[str, Any]:
    try:
        result = run(argv, check=False)
        return {
            "argv": argv,
            "exit_code": result.returncode,
            "stdout": redact_string(result.stdout[-limit:]),
            "stderr": redact_string(result.stderr[-limit:]),
        }
    except Exception as exc:
        return {"argv": argv, "error": redact_string(str(exc))}


def diagnostics_command(args: argparse.Namespace) -> int:
    state = state_or_fail()
    safe_state = {
        key: value
        for key, value in state.items()
        if key
        in {
            "HEIDI_VERSION",
            "HEIDI_CHANNEL",
            "HEIDI_MODE",
            "HEIDI_TOPOLOGY",
            "HEIDI_SPLIT_ROLE",
            "HEIDI_SERVICE_SCOPE",
            "HEIDI_SUPERVISOR",
            "HEIDI_PUBLIC_TRANSPORT",
            "HEIDI_CPTR_URL",
            "HEIDI_MCP_URL",
            "HEIDI_CPTR_DATA_DIR",
            "HEIDI_RELEASE_DIR",
        }
    }
    diagnostics: dict[str, Any] = {
        "schema": "heidi.diagnostics.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state": redact_mapping(safe_state),
        "disk": command_output(["df", "-h", str(Path.home())]),
    }
    if shutil.which("tailscale"):
        diagnostics["tailscale"] = command_output(["tailscale", "status", "--json"])
    base = service_scope(state)
    diagnostics["services"] = {}
    for unit in state.get("HEIDI_SERVICE_UNITS", "heidi-cptr.service heidi-mcp.service").split():
        journal_args = ["journalctl"]
        if base == ["systemctl", "--user"]:
            journal_args.append("--user")
        journal_args.extend(["-u", unit, "-n", "60", "--no-pager"])
        diagnostics["services"][unit] = {
            "status": command_output([*base, "status", unit, "--no-pager"]),
            "logs": command_output(journal_args),
        }
    for name, url in (("cptr_live", state.get("HEIDI_CPTR_URL", "") + "/api/health/live"), ("mcp_health", state.get("HEIDI_MCP_LOCAL_URL", "") + "/health")):
        if url.startswith("http"):
            diagnostics[name] = command_output(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "5", url])
    output = Path(args.output or config_dir() / f"diagnostics-{now_tag()}.json").expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(redact_mapping(diagnostics), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    print(f"Redacted diagnostics: {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="heidi-lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    backup = sub.add_parser("backup")
    backup.add_argument("--output-dir")
    backup.set_defaults(func=backup_command)

    restore = sub.add_parser("restore")
    restore.add_argument("archive")
    restore.add_argument("--no-pre-backup", action="store_true")
    restore.set_defaults(func=restore_command)

    rollback = sub.add_parser("rollback")
    rollback.add_argument("version")
    rollback.add_argument("--no-backup", action="store_true")
    rollback.add_argument("--no-verify", action="store_true")
    rollback.set_defaults(func=rollback_command)

    diagnostics = sub.add_parser("diagnostics")
    diagnostics.add_argument("--output")
    diagnostics.set_defaults(func=diagnostics_command)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {redact_string(str(exc))}", file=sys.stderr)
        raise SystemExit(1)
