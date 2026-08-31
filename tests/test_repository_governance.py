from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_heidi_cli_is_the_documented_canonical_product_boundary():
    governance = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
    provenance = (ROOT / "docs" / "SOURCE_PROVENANCE.md").read_text(encoding="utf-8")

    assert "heidi-dang/heidi-cli" in governance
    assert "canonical repository" in governance.lower()
    assert "heidi-dang/computer" in governance
    assert "heidi-dang/chatgpt-computer-plugin" in governance
    assert "audited sync" in governance.lower()
    assert "26-tool production MCP contract" in governance
    assert "heidi-dang/chatgpt-computer-plugin" in provenance
    assert "heidi-dang/computer" in provenance


def test_default_branch_tracks_only_canonical_persistent_workflows():
    workflow_dir = ROOT / ".github" / "workflows"
    tracked = {path.name for path in workflow_dir.glob("*.yml")}
    assert tracked == {"ci.yml", "release.yml"}


def test_fdx_ci_declares_node_runtime_for_npm_backed_policy_verification():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    fdx_job = workflow.split("\n  fdx:\n", 1)[1]
    assert "actions/setup-node@v4" in fdx_job
    assert "node-version: 22" in fdx_job or "node-version: '22'" in fdx_job


def test_monorepo_does_not_use_nested_repository_indirection():
    assert not (ROOT / ".gitmodules").exists()
    governance = (ROOT / "docs" / "REPOSITORY_GOVERNANCE.md").read_text(encoding="utf-8")
    assert "exclude nested `.git`" in governance
