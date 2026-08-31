from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release-manifest.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_compatibility_verifier():
    path = ROOT / "scripts" / "verify-compatibility.py"
    spec = importlib.util.spec_from_file_location("verify_compatibility_release", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_release_compatibility_matches_canonical_mcp_inventory():
    verifier = load_compatibility_verifier()
    compatibility = json.loads((ROOT / "release" / "compatibility.json").read_text(encoding="utf-8"))
    result = verifier.verify(ROOT, compatibility["heidi_version"])
    names = verifier.compact_tool_names(ROOT)
    assert result["mcp_tool_count"] == len(names)
    assert result["mcp_tool_count"] == compatibility["mcp"]["registered_action_count"]
    assert names.count("cptr_workspace_lifecycle") == 1


def test_release_manifest_is_deterministic_and_ed25519_verifiable(tmp_path: Path):
    source = tmp_path / "source.tar.gz"
    source.write_bytes(b"heidi-source-fixture\n")
    compatibility = tmp_path / "compatibility.json"
    compatibility.write_text('{"heidi_version":"2.0.0"}\n', encoding="utf-8")
    runtime_lock = tmp_path / "runtime-lock.json"
    runtime_lock.write_text(
        json.dumps(
            {
                "schema": "heidi.runtime-lock.v1",
                "runtimes": {
                    "node": {
                        "linux-x64": {
                            "version": "v22.23.2",
                            "url": "https://example.invalid/node.tar.xz",
                            "sha256": "a" * 64,
                            "format": "tar.xz",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)], check=True)
    subprocess.run(
        ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
        check=True,
    )
    output = tmp_path / "heidi-release.json"
    signature = tmp_path / "heidi-release.json.sig"
    command = [
        sys.executable,
        str(SCRIPT),
        "--version",
        "2.0.0",
        "--channel",
        "stable",
        "--source-archive",
        str(source),
        "--source-url",
        "https://github.com/heidi-dang/heidi-cli/releases/download/v2.0.0/heidi-cli-2.0.0.tar.gz",
        "--git-sha",
        "a" * 40,
        "--compatibility",
        str(compatibility),
        "--runtime-lock",
        str(runtime_lock),
        "--output",
        str(output),
        "--signing-key",
        str(private_key),
        "--signature-output",
        str(signature),
    ]
    subprocess.run(command, check=True)
    first = output.read_bytes()
    subprocess.run(command, check=True)
    assert output.read_bytes() == first
    payload = json.loads(first)
    assert payload["schema"] == "heidi.release.v1"
    assert payload["version"] == "2.0.0"
    assert payload["channel"] == "stable"
    assert payload["source"]["sha256"] == sha(source)
    assert payload["source"]["git_sha"] == "a" * 40
    assert payload["compatibility_sha256"] == sha(compatibility)
    assert payload["runtimes"]["node"]["linux-x64"]["sha256"] == "a" * 64
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            str(public_key),
            "-rawin",
            "-in",
            str(output),
            "-sigfile",
            str(signature),
        ],
        check=True,
    )


def test_release_manifest_rejects_unpinned_runtime(tmp_path: Path):
    source = tmp_path / "source.tar.gz"
    source.write_bytes(b"source")
    compatibility = tmp_path / "compatibility.json"
    compatibility.write_text("{}\n", encoding="utf-8")
    runtime_lock = tmp_path / "runtime-lock.json"
    runtime_lock.write_text(
        json.dumps(
            {
                "schema": "heidi.runtime-lock.v1",
                "runtimes": {
                    "cloudflared": {
                        "linux-x64": {
                            "url": "https://example.invalid/cloudflared",
                            "sha256": "not-a-hash",
                            "format": "binary",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--version",
            "2.0.0",
            "--channel",
            "stable",
            "--source-archive",
            str(source),
            "--source-url",
            "https://example.invalid/source.tar.gz",
            "--git-sha",
            "b" * 40,
            "--compatibility",
            str(compatibility),
            "--runtime-lock",
            str(runtime_lock),
            "--output",
            str(tmp_path / "out.json"),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "sha256" in result.stderr.lower()
