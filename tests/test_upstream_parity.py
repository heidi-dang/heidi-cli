from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit-upstream-parity.py"

COMPUTER_SHA = "ae2996a672ad4b595617384b7c5ee8cced3e304d"
PLUGIN_SHA = "70c3962e74a75bde2fd3beb1bfaea7ac0a73b517"

REQUIRED = {
    "computer:mcp_traffic",
    "computer:mcp_activity",
    "computer:mcp_diagnostics",
    "computer:system_metrics",
    "computer:mcp_topology_ui",
    "computer:lsp_manager",
    "computer:interactive_pty",
    "computer:direct_coding_runtime_hardening",
    "computer:hybrid_benchmark",
    "plugin:mcp_traffic_delivery",
    "plugin:mcp_activity_delivery",
    "plugin:mcp_diagnostics_delivery",
    "plugin:interactive_pty_controls",
    "plugin:lsp_controls",
    "plugin:iphone_terminal",
    "plugin:hybrid_benchmark",
    "plugin:prompt_sse_status",
}


def load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_upstream_parity", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_tracks_authoritative_upstream_revisions_and_required_capabilities():
    module = load_audit_module()

    assert module.COMPUTER_SHA == COMPUTER_SHA
    assert module.PLUGIN_SHA == PLUGIN_SHA
    assert set(module.CAPABILITY_IDS) >= REQUIRED


def test_audit_capabilities_reports_missing_evidence(tmp_path: Path):
    module = load_audit_module()
    (tmp_path / "present.txt").write_text("ok", encoding="utf-8")

    result = module.audit_capabilities(
        tmp_path,
        [
            module.capability(
                "present",
                "computer",
                COMPUTER_SHA,
                "cptr/services/example.py",
                ["present.txt"],
                "adapted",
            ),
            module.capability(
                "missing",
                "plugin",
                PLUGIN_SHA,
                "server/example.ts",
                ["missing.txt"],
                "compact-gateway",
            ),
        ],
    )

    assert result["coverage_percent"] == 50.0
    assert result["unmapped"] == ["missing"]
    assert result["capabilities"] == ["present", "missing"]


def test_audit_capabilities_rejects_wrong_source_revision(tmp_path: Path):
    module = load_audit_module()
    (tmp_path / "present.txt").write_text("ok", encoding="utf-8")

    result = module.audit_capabilities(
        tmp_path,
        [
            module.capability(
                "wrong-sha",
                "computer",
                "0" * 40,
                "cptr/services/example.py",
                ["present.txt"],
                "adapted",
            )
        ],
    )

    assert result["coverage_percent"] == 0.0
    assert result["unmapped"] == ["wrong-sha"]
