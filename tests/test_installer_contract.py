from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_compatibility_verifier():
    path = ROOT / "scripts" / "verify-compatibility.py"
    spec = importlib.util.spec_from_file_location("verify_compatibility", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_headless_systemd_falls_back_to_system_scope_without_changing_service_identity():
    core = read("scripts/install-core.sh")
    lib = read("scripts/install-lib.sh")
    assert "select_service_scope" in core
    assert "write_service_unit" in core
    assert "systemctl_scope" in lib
    assert 'SERVICE_SCOPE="system"' in lib
    assert "User=$SERVICE_USER" in core
    assert "Group=$SERVICE_GROUP" in core


def test_cli_has_release_lifecycle_and_diagnostics_commands():
    source = read("bin/heidi")
    for command in ["rollback", "backup", "restore", "diagnostics", "--channel"]:
        assert command in source


def test_deploy_cli_supports_explicit_production_or_dev_mode_only():
    source = read("bin/heidi")
    assert "deploy [--mode production|dev]" in source
    assert 'case "$mode" in' in source
    assert "dev|development" in source
    assert 'HEIDI_DEPLOY_MODE="$mode"' in source
    assert "update [--channel stable|beta|edge]" in source
    assert "update [--mode" not in source


def test_public_redeploy_reuses_saved_cloudflare_access_app_id():
    source = read("scripts/install-core.sh")
    assert 'state_default HEIDI_CF_ACCESS_APP_ID' in source
    assert 'CF_ARGS+=(--access-app-id "$CF_ACCESS_APP_ID")' in source


def test_deploy_cli_exports_loaded_release_state_to_installer(tmp_path):
    config_dir = tmp_path / "config"
    release_dir = tmp_path / "release"
    repo_dir = release_dir / "source"
    scripts_dir = repo_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    config_dir.mkdir()
    (config_dir / "state.env").write_text(
        "\n".join(
            [
                'HEIDI_HOME="/tmp/heidi-home"',
                'HEIDI_VERSION="2.1.0"',
                'HEIDI_CHANNEL="stable"',
                f'HEIDI_RELEASE_DIR="{release_dir}"',
                f'HEIDI_REPO_DIR="{repo_dir}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (scripts_dir / "install-core.sh").write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\n" "${HEIDI_HOME:-}" "${HEIDI_VERSION:-}" "${HEIDI_CHANNEL:-}" "${HEIDI_RELEASE_DIR:-}" "${HEIDI_REPO_DIR:-}" "${HEIDI_DEPLOY_MODE:-}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HEIDI_CONFIG_DIR"] = str(config_dir)
    result = subprocess.run(
        ["bash", str(ROOT / "bin" / "heidi"), "deploy", "--mode", "dev"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "/tmp/heidi-home",
        "2.1.0",
        "stable",
        str(release_dir),
        str(repo_dir),
        "development",
    ]


def test_development_mcp_service_uses_bundled_node_hot_reload_runner():
    source = read("scripts/install-core.sh")
    assert "HEIDI_DEPLOY_MODE" in source
    assert 'MCP_EXEC="$NODE_BIN $HEIDI_HOME/current/source/apps/mcp/scripts/dev.mjs"' in source
    assert 'MCP_EXEC="$NPM_BIN --prefix $HEIDI_HOME/current/source/apps/mcp run dev"' not in source


def test_production_mcp_enables_bounded_workbench_disables_hot_reload_and_uses_compiled_runner():
    source = read("scripts/install-core.sh")
    checker = read("apps/mcp/scripts/check-deployed-contract.mjs")
    assert "env_line CPTR_WORKBENCH_UI 1" in source
    assert 'env_line CPTR_COMPAT_WORKBENCH "$( [[ "$MODE" == production ]] && echo 0 || echo 1 )"' in source
    assert 'env_line CPTR_HOT_RELOAD "$( [[ "$MODE" == production ]] && echo 0 || echo 1 )"' in source
    assert 'MCP_EXEC="$NODE_BIN $HEIDI_HOME/current/source/apps/mcp/dist/server/index.js"' in source
    assert '[[ "$MODE" == production ]] || MCP_EXEC="$NODE_BIN $HEIDI_HOME/current/source/apps/mcp/scripts/dev.mjs"' in source
    assert "production MCP must expose the CPTR Workbench UI" in checker
    assert "production Workbench hot reload must remain disabled" in checker
    assert 'const expectedResource = "ui://cptr/live-workbench.html"' in checker


def test_production_mcp_requires_and_verifies_signed_git_provenance():
    bootstrap = read("install.sh")
    core = read("scripts/install-core.sh")
    verifier = read("scripts/verify-stack.sh")
    assert "source.git_sha" in bootstrap
    assert 'export HEIDI_SOURCE_GIT_SHA="$SOURCE_GIT_SHA"' in bootstrap
    assert "production MCP deployment requires signed source Git commit provenance" in core
    assert 'env_line GIT_COMMIT_SHA "$SOURCE_GIT_SHA"' in core
    assert 'env_line HEIDI_SOURCE_GIT_SHA "$SOURCE_GIT_SHA"' in core
    assert 'env_line HEIDI_CONTROL_PROFILE "$CONTROL_PROFILE"' in core
    assert "Production MCP release SHA matches signed source provenance" in verifier
    assert 'data.get("release") == expected' in verifier


def test_cptr_execution_environment_includes_bundled_runtime_path():
    source = read("scripts/install-core.sh")
    cptr_block = source.split('>"$CPTR_ENV_FILE"', 1)[0].rsplit("if [[ \"$INCLUDES_BACKEND\" == 1 ]]", 1)[-1]
    assert 'env_line PATH "$HEIDI_HOME/current/venv/bin:$HEIDI_HOME/current/runtime/node/bin:$HEIDI_HOME/current/bin:' in cptr_block
    assert ":/snap/bin\"" in cptr_block


def test_production_test_runner_and_managed_chrome_dependencies_are_provisioned():
    core = read("scripts/install-core.sh")
    lib = read("scripts/install-lib.sh")
    pyproject = read("apps/cptr/pyproject.toml")
    dockerfile = read("apps/cptr/Dockerfile")
    tools = read("apps/cptr/cptr/utils/tools.py")

    assert "ensure_managed_chrome" in lib
    assert "ensure_managed_chrome" in core
    assert "apt_install chromium-browser" in lib
    assert "apt_install chromium" in lib
    assert '"pytest>=8.4,<9"' in pyproject
    assert '"pytest-asyncio>=1.4,<2"' in pyproject
    assert "COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node" in dockerfile
    assert "npm-cli.js /usr/local/bin/npm" in dockerfile
    assert "FROM browser AS default" in dockerfile
    assert "_direct_coding_runtime_env" in tools
    assert 'heidi_home / "current" / "runtime" / "node" / "bin"' in tools
    assert 'Path(sys.executable).parent' in tools


def test_verifier_generates_tailored_ai_repair_prompt_on_failure():
    source = read("scripts/verify-stack.sh")
    assert "remediation.py" in source
    assert "HEIDI AI REPAIR PROMPT" in read("scripts/remediation.py")


def test_verifier_uses_bundled_node_runtime_for_contract_check():
    source = read("scripts/verify-stack.sh")
    assert "runtime/node/bin/node" in source
    assert 'dirname "$REPO_DIR"' in source
    assert '"$node_binary" "$REPO_DIR/apps/mcp/scripts/check-deployed-contract.mjs"' in source


def test_bootstrap_has_signed_release_trust_boundary():
    source = read("install.sh")
    assert "heidi-release.json" in source
    assert "heidi-release.json.sig" in source
    assert "openssl" in source
    assert "release/signing-public.pem" in source or "BEGIN PUBLIC KEY" in source


def test_bootstrap_revalidates_all_signed_source_files_before_reusing_release():
    source = read("install.sh")
    assert "verify_existing_signed_source" in source
    assert 'verify_existing_signed_source "$STAGE/source" "$RELEASE_DIR/source"' in source
    assert "modified signed source files" in source
    assert "installed source directory must not be a symlink" in source
    assert "target.is_symlink() or not target.is_dir()" in source


def test_compatibility_manifest_matches_canonical_runtime_inventory_and_sandbox():
    compatibility = json.loads(read("release/compatibility.json"))
    verifier = load_compatibility_verifier()
    result = verifier.verify(ROOT, compatibility["heidi_version"])
    assert result["mcp_tool_count"] == compatibility["mcp"]["registered_action_count"]
    assert "cptr_workspace_lifecycle" in verifier.compact_tool_names(ROOT)
    assert compatibility["deployment"]["topologies"] == ["all-in-one", "split-tailscale"]
    assert "sandbox" in compatibility


def test_installer_defaults_to_owner_full_profile():
    source = read("scripts/install-core.sh")
    bootstrap = read("scripts/bootstrap-control-token.py")
    assert 'if [[ -n "${HEIDI_CONTROL_PROFILE:-}" ]]; then' in source
    assert 'CONTROL_PROFILE="$HEIDI_CONTROL_PROFILE"' in source
    assert 'state_default HEIDI_CONTROL_PROFILE owner-full' in source
    assert '[[ "$CONTROL_PROFILE" != standard ]] || CONTROL_PROFILE=owner-full' in source
    assert '[[ "$CONTROL_PROFILE" != developer ]] || CONTROL_PROFILE=owner-full' in source
    assert '[[ "$CONTROL_PROFILE" != full ]] || CONTROL_PROFILE=owner-full' in source
    assert 'standard|developer|owner-full)' in source
    assert "HEIDI_CONTROL_PROFILE must be standard, developer, or owner-full" in source
    assert "Enable owner-full control" in source
    assert "confirmed managed-workspace deletion" in source
    assert "CONTROL_PROFILE=full" not in source
    assert 'choices=("standard", "developer", "owner-full", "full")' in bootstrap
    assert 'default="owner-full"' in bootstrap


def test_runtime_lock_pins_every_downloaded_runtime_for_both_linux_architectures():
    lock = json.loads(read("release/runtime-lock.json"))
    assert lock["schema"] == "heidi.runtime-lock.v1"
    for runtime in ["node", "rustup", "cloudflared", "caddy"]:
        assert set(lock["runtimes"][runtime]) == {"linux-x64", "linux-arm64"}
        for artifact in lock["runtimes"][runtime].values():
            assert artifact["url"].startswith("https://")
            assert len(artifact["sha256"]) == 64
            int(artifact["sha256"], 16)


def test_rustup_runtime_uses_versioned_immutable_archive_urls():
    lock = json.loads(read("release/runtime-lock.json"))
    for artifact in lock["runtimes"]["rustup"].values():
        version = artifact["version"]
        assert version != "current"
        assert f"/rustup/archive/{version}/" in artifact["url"]
        assert "/rustup/dist/" not in artifact["url"]


def test_noninteractive_upgrade_reuses_only_secure_matching_public_configuration():
    source = read("scripts/install-core.sh")
    assert "secure_owner_file" in source
    assert "existing_public_config_reusable" in source
    assert '"${HEIDI_NONINTERACTIVE:-0}" == 1' in source
    assert '"$PREVIOUS_PUBLIC_TRANSPORT" == "$PUBLIC_TRANSPORT"' in source
    assert '"$PREVIOUS_MCP_DOMAIN" == "$MCP_DOMAIN"' in source
    assert '"$PREVIOUS_MCP_ALLOWED_EMAIL" == "$MCP_ALLOWED_EMAIL"' in source
    assert 'secure_owner_file "$MCP_ENV_FILE"' in source
    assert 'env_file_default "$MCP_ENV_FILE" MCP_OAUTH_ALLOWED_EMAIL' in source
    assert 'state_default HEIDI_MCP_ALLOWED_EMAIL "$LEGACY_MCP_ALLOWED_EMAIL"' in source
    assert 'env_file_default "$MCP_ENV_FILE" CLOUDFLARE_ACCESS_ISSUER' in source
    assert 'env_file_default "$MCP_ENV_FILE" CLOUDFLARE_ACCESS_AUDIENCE' in source
    assert 'secure_owner_file "$MCP_OAUTH_CLIENT_STATE_FILE"' in source
    assert "Reusing existing verified public MCP configuration for non-interactive upgrade" in source
    assert 'HEIDI_CONFIG_DIR="$CONFIG_DIR" "$HEIDI_HOME/current/source/scripts/verify-stack.sh"' in source


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
    assert "scripts/verify-compatibility.py" in source
    assert '--git-sha "$GITHUB_SHA"' in source


def test_versioned_release_assets_are_never_clobbered():
    source = read(".github/workflows/release.yml")
    assert "--clobber" not in source
    assert "already exists; refusing to replace immutable release assets" in source
