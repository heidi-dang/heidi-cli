#!/usr/bin/env python3
"""Audit Heidi's source-controlled functional mapping to official upstreams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

COMPUTER_SHA = "ae2996a672ad4b595617384b7c5ee8cced3e304d"
PLUGIN_SHA = "70c3962e74a75bde2fd3beb1bfaea7ac0a73b517"


class Capability(TypedDict):
    capability_id: str
    upstream: str
    source_sha: str
    source_evidence: str
    heidi_evidence: list[str]
    mapping: str


def capability(
    capability_id: str,
    upstream: str,
    source_sha: str,
    source_evidence: str,
    heidi_evidence: list[str],
    mapping: str,
) -> Capability:
    return {
        "capability_id": capability_id,
        "upstream": upstream,
        "source_sha": source_sha,
        "source_evidence": source_evidence,
        "heidi_evidence": heidi_evidence,
        "mapping": mapping,
    }


CAPABILITIES: list[Capability] = [
    capability(
        "computer:mcp_traffic",
        "computer",
        COMPUTER_SHA,
        "cptr/services/mcp_traffic.py",
        ["apps/cptr/cptr/services/mcp_traffic.py", "apps/cptr/cptr/routers/mcp.py"],
        "adapted",
    ),
    capability(
        "computer:mcp_activity",
        "computer",
        COMPUTER_SHA,
        "cptr/services/mcp_activity.py",
        ["apps/cptr/cptr/services/mcp_activity.py", "apps/cptr/cptr/routers/mcp.py"],
        "adapted",
    ),
    capability(
        "computer:mcp_diagnostics",
        "computer",
        COMPUTER_SHA,
        "cptr/services/mcp_diagnostics.py",
        ["apps/cptr/cptr/services/mcp_diagnostics.py", "apps/cptr/cptr/routers/mcp.py"],
        "adapted",
    ),
    capability(
        "computer:system_metrics",
        "computer",
        COMPUTER_SHA,
        "cptr/services/system_metrics.py",
        ["apps/cptr/cptr/services/system_metrics.py"],
        "adapted",
    ),
    capability(
        "computer:mcp_topology_ui",
        "computer",
        COMPUTER_SHA,
        "cptr/frontend/src/routes/mcp/+page.svelte",
        [
            "apps/cptr/cptr/frontend/src/routes/mcp/+page.svelte",
            "apps/cptr/cptr/frontend/src/lib/components/mcp/McpTopology.svelte",
        ],
        "adapted",
    ),
    capability(
        "computer:lsp_manager",
        "computer",
        COMPUTER_SHA,
        "cptr/services/lsp_manager.py",
        ["apps/cptr/cptr/services/lsp_manager.py", "apps/cptr/cptr/routers/coding.py"],
        "adapted",
    ),
    capability(
        "computer:interactive_pty",
        "computer",
        COMPUTER_SHA,
        "cptr/routers/coding.py",
        ["apps/cptr/cptr/routers/coding.py", "apps/cptr/tests/test_terminal_parity.py"],
        "adapted",
    ),
    capability(
        "computer:direct_coding_runtime_hardening",
        "computer",
        COMPUTER_SHA,
        "cptr/services/fdx_intelligence.py",
        [
            "apps/cptr/cptr/services/fdx_intelligence.py",
            "apps/cptr/cptr/utils/runtime.py",
            "apps/cptr/cptr/utils/tools.py",
        ],
        "adapted",
    ),
    capability(
        "computer:hybrid_benchmark",
        "computer",
        COMPUTER_SHA,
        "cptr/services/coding_benchmark.py",
        [
            "apps/cptr/cptr/services/coding_benchmark.py",
            "apps/cptr/cptr/services/coding_benchmark_grader.py",
        ],
        "adapted",
    ),
    capability(
        "computer:durable_usage",
        "computer",
        COMPUTER_SHA,
        "cptr/services/mcp_usage_store.py",
        [
            "apps/cptr/cptr/services/mcp_usage_store.py",
            "apps/cptr/cptr/migrations/versions/0018_mcp_usage_benchmarks.py",
        ],
        "adapted",
    ),
    capability(
        "computer:frontend_accessibility_and_chunks",
        "computer",
        COMPUTER_SHA,
        "cptr/frontend/vite.config.ts",
        [
            "apps/cptr/cptr/frontend/vite.config.ts",
            "apps/cptr/cptr/frontend/scripts/check-production-build.mjs",
        ],
        "adapted",
    ),
    capability(
        "plugin:mcp_traffic_delivery",
        "plugin",
        PLUGIN_SHA,
        "server/mcp-traffic.ts",
        ["apps/mcp/server/mcp-traffic.ts"],
        "adapted",
    ),
    capability(
        "plugin:mcp_activity_delivery",
        "plugin",
        PLUGIN_SHA,
        "server/mcp-activity.ts",
        ["apps/mcp/server/mcp-activity.ts"],
        "adapted",
    ),
    capability(
        "plugin:mcp_diagnostics_delivery",
        "plugin",
        PLUGIN_SHA,
        "server/mcp-diagnostics.ts",
        ["apps/mcp/server/mcp-diagnostics.ts"],
        "adapted",
    ),
    capability(
        "plugin:interactive_pty_controls",
        "plugin",
        PLUGIN_SHA,
        "server/mcp.ts:cptr_code_send_input/cptr_code_resize_command/cptr_code_signal_command",
        [
            "apps/mcp/server/compact-gateways.ts",
            "apps/mcp/tests/terminal-lsp-gateways.test.ts",
        ],
        "compact-gateway",
    ),
    capability(
        "plugin:lsp_controls",
        "plugin",
        PLUGIN_SHA,
        "server/mcp.ts:cptr_lsp_discover/cptr_lsp_start/cptr_lsp_request/cptr_lsp_stop",
        [
            "apps/mcp/server/compact-gateways.ts",
            "apps/mcp/tests/terminal-lsp-gateways.test.ts",
        ],
        "compact-gateway",
    ),
    capability(
        "plugin:iphone_terminal",
        "plugin",
        PLUGIN_SHA,
        "web/src/terminal-view.tsx",
        ["apps/mcp/web/src/terminal-view.tsx", "apps/mcp/web/src/workbench.css"],
        "adapted",
    ),
    capability(
        "plugin:hybrid_benchmark",
        "plugin",
        PLUGIN_SHA,
        "server/mcp.ts:cptr_benchmark_*",
        ["apps/mcp/server/compact-gateways.ts", "apps/mcp/tests/usage-benchmark.test.ts"],
        "compact-gateway",
    ),
    capability(
        "plugin:prompt_sse_status",
        "plugin",
        PLUGIN_SHA,
        "web/src/workbench.tsx@70c3962",
        ["apps/mcp/web/src/workbench.tsx", "apps/mcp/tests/terminal-view.test.ts"],
        "adapted",
    ),
]

CAPABILITY_IDS = tuple(item["capability_id"] for item in CAPABILITIES)


def _expected_sha(upstream: str) -> str | None:
    if upstream == "computer":
        return COMPUTER_SHA
    if upstream == "plugin":
        return PLUGIN_SHA
    return None


def audit_capabilities(root: Path, capabilities: list[Capability]) -> dict[str, object]:
    resolved_root = root.resolve()
    unmapped: list[str] = []
    by_upstream: dict[str, dict[str, int]] = {}

    for item in capabilities:
        upstream = item["upstream"]
        stats = by_upstream.setdefault(upstream, {"total": 0, "mapped": 0})
        stats["total"] += 1
        expected_sha = _expected_sha(upstream)
        sha_ok = expected_sha is not None and item["source_sha"] == expected_sha
        evidence_ok = bool(item["heidi_evidence"]) and all(
            (resolved_root / relative).exists() for relative in item["heidi_evidence"]
        )
        mapping_ok = item["mapping"] in {"verbatim", "adapted", "compact-gateway"}
        if sha_ok and evidence_ok and mapping_ok:
            stats["mapped"] += 1
        else:
            unmapped.append(item["capability_id"])

    total = len(capabilities)
    mapped = total - len(unmapped)
    return {
        "capabilities": [item["capability_id"] for item in capabilities],
        "computer": by_upstream.get("computer", {"total": 0, "mapped": 0}),
        "plugin": by_upstream.get("plugin", {"total": 0, "mapped": 0}),
        "unmapped": unmapped,
        "coverage_percent": round((mapped / total) * 100, 2) if total else 100.0,
    }


def audit_parity(root: Path) -> dict[str, object]:
    return audit_capabilities(root, CAPABILITIES)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result = audit_parity(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["unmapped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
