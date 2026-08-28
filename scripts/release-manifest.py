#!/usr/bin/env python3
"""Build and optionally sign Heidi's deterministic release manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CHANNELS = {"stable", "beta", "edge"}
PLATFORMS = {"linux-x64", "linux-arm64"}
FORMATS = {"binary", "tar.xz", "tar.gz"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_runtime_lock(lock: dict[str, Any]) -> dict[str, Any]:
    if lock.get("schema") != "heidi.runtime-lock.v1":
        raise ValueError("runtime lock schema must be heidi.runtime-lock.v1")
    runtimes = lock.get("runtimes")
    if not isinstance(runtimes, dict) or not runtimes:
        raise ValueError("runtime lock must contain runtimes")
    normalized: dict[str, Any] = {}
    for runtime, platforms in sorted(runtimes.items()):
        if not isinstance(runtime, str) or not runtime or not isinstance(platforms, dict):
            raise ValueError("runtime lock contains an invalid runtime entry")
        normalized_platforms: dict[str, Any] = {}
        for platform, entry in sorted(platforms.items()):
            if platform not in PLATFORMS or not isinstance(entry, dict):
                raise ValueError(f"unsupported runtime platform: {runtime}/{platform}")
            url = entry.get("url")
            checksum = entry.get("sha256")
            artifact_format = entry.get("format")
            version = entry.get("version")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise ValueError(f"runtime url must be pinned HTTPS: {runtime}/{platform}")
            if not isinstance(checksum, str) or not SHA256_RE.fullmatch(checksum):
                raise ValueError(f"runtime sha256 is invalid: {runtime}/{platform}")
            if artifact_format not in FORMATS:
                raise ValueError(f"runtime format is invalid: {runtime}/{platform}")
            if not isinstance(version, str) or not version:
                raise ValueError(f"runtime version is missing: {runtime}/{platform}")
            clean = {
                "version": version,
                "url": url,
                "sha256": checksum,
                "format": artifact_format,
            }
            member = entry.get("member")
            if member is not None:
                if not isinstance(member, str) or not member or "/" in member or member in {".", ".."}:
                    raise ValueError(f"runtime archive member is invalid: {runtime}/{platform}")
                clean["member"] = member
            normalized_platforms[platform] = clean
        normalized[runtime] = normalized_platforms
    return normalized


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.source_archive).resolve()
    compatibility = Path(args.compatibility).resolve()
    runtime_lock = Path(args.runtime_lock).resolve()
    for path in (source, compatibility, runtime_lock):
        if not path.is_file():
            raise ValueError(f"required release input does not exist: {path}")
    if args.channel not in CHANNELS:
        raise ValueError(f"unsupported release channel: {args.channel}")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.version):
        raise ValueError(f"invalid Heidi version: {args.version}")
    if not args.source_url.startswith("https://"):
        raise ValueError("source URL must use HTTPS")
    compatibility_payload = load_json(compatibility)
    compatibility_version = compatibility_payload.get("heidi_version")
    if compatibility_version not in (None, args.version):
        raise ValueError(
            f"compatibility manifest version {compatibility_version!r} does not match release {args.version!r}"
        )
    runtimes = validate_runtime_lock(load_json(runtime_lock))
    return {
        "schema": "heidi.release.v1",
        "version": args.version,
        "channel": args.channel,
        "source": {
            "url": args.source_url,
            "sha256": sha256_file(source),
        },
        "compatibility_sha256": sha256_file(compatibility),
        "runtime_lock_sha256": sha256_file(runtime_lock),
        "runtimes": runtimes,
    }


def sign_manifest(manifest: Path, private_key: Path, signature: Path) -> None:
    if not private_key.is_file():
        raise ValueError(f"signing key does not exist: {private_key}")
    signature.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-inkey",
            str(private_key),
            "-rawin",
            "-in",
            str(manifest),
            "-out",
            str(signature),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", required=True, choices=sorted(CHANNELS))
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--compatibility", required=True)
    parser.add_argument("--runtime-lock", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--signing-key")
    parser.add_argument("--signature-output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.signing_key) != bool(args.signature_output):
        raise ValueError("--signing-key and --signature-output must be provided together")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(build_manifest(args)))
    if args.signing_key:
        sign_manifest(output, Path(args.signing_key).resolve(), Path(args.signature_output).resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
