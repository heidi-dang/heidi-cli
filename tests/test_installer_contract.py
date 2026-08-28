from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_installer_exposes_all_in_one_and_split_tailscale_topologies():
    source = read("scripts/install-core.sh")
    assert "all-in-one" in source
    assert "split-tailscale" in source
    assert "backend" in source
    assert "mcp" in source
    assert "systemd" in source
    assert "recommended" in source.lower()
    assert "tailscale" in source.lower()
    assert "caddy" in source.lower()
    assert "Cloudflare API token" in source


def test_split_entrypoints_are_explicit_machine_roles():
    backend = read("scripts/install-split-backend.sh")
    mcp = read("scripts/install-split-mcp.sh")
    assert "HEIDI_TOPOLOGY=split-tailscale" in backend
    assert "HEIDI_SPLIT_ROLE=backend" in backend
    assert "HEIDI_TOPOLOGY=split-tailscale" in mcp
    assert "HEIDI_SPLIT_ROLE=mcp" in mcp


def test_cli_has_release_lifecycle_and_diagnostics_commands():
    source = read("bin/heidi")
    for command in ["rollback", "backup", "restore", "diagnostics", "--channel"]:
        assert command in source


def test_verifier_generates_tailored_ai_repair_prompt_on_failure():
    source = read("scripts/verify-stack.sh")
    assert "remediation.py" in source
    assert "HEIDI AI REPAIR PROMPT" in read("scripts/remediation.py")


def test_bootstrap_has_signed_release_trust_boundary():
    source = read("install.sh")
    assert "heidi-release.json" in source
    assert "heidi-release.json.sig" in source
    assert "openssl" in source
    assert "release/signing-public.pem" in source or "BEGIN PUBLIC KEY" in source


def test_compatibility_manifest_declares_v2_compact_contract_and_sandbox():
    source = read("release/compatibility.json")
    assert '"registered_action_count": 20' in source
    assert '"topologies": ["all-in-one", "split-tailscale"]' in source
    assert '"sandbox"' in source


def test_runtime_lock_pins_every_downloaded_runtime_for_both_linux_architectures():
    import json

    lock = json.loads(read("release/runtime-lock.json"))
    assert lock["schema"] == "heidi.runtime-lock.v1"
    for runtime in ["node", "rustup", "cloudflared", "caddy"]:
        assert set(lock["runtimes"][runtime]) == {"linux-x64", "linux-arm64"}
        for artifact in lock["runtimes"][runtime].values():
            assert artifact["url"].startswith("https://")
            assert len(artifact["sha256"]) == 64
            int(artifact["sha256"], 16)


def test_caddy_signed_tarball_is_extracted_after_checksum_verification():
    source = read("scripts/install-lib.sh")
    assert "manifest_runtime_field caddy" in source
    assert "tar -xzf" in source
    assert "member" in source


def test_release_workflow_builds_signs_and_publishes_channel_assets():
    source = read(".github/workflows/release.yml")
    assert "HEIDI_RELEASE_SIGNING_KEY_B64" in source
    assert "release-manifest.py" in source
    assert "heidi-release.json.sig" in source
    assert "options: [stable, beta, edge]" in source
    assert 'CHANNEL_TAG="channel-${CHANNEL}"' in source
