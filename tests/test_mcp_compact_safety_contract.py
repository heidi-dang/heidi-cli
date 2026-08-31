from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP = ROOT / "apps" / "mcp"


def test_compact_contract_splits_read_surfaces_from_mixed_control_gateways():
    release = (MCP / "server" / "release.ts").read_text(encoding="utf-8")

    expected_split_tools = {
        "cptr_workbench_sessions_read",
        "cptr_workbench_sessions_control",
        "cptr_ssh_read",
        "cptr_ssh_control",
        "cptr_chrome_read",
        "cptr_chrome_control",
        "cptr_delegate_task_read",
        "cptr_delegate_task_control",
        "cptr_delegate_monitor_read",
        "cptr_delegate_monitor_control",
    }
    for tool in expected_split_tools:
        assert f'"{tool}"' in release

    for obsolete_mixed_tool in (
        "cptr_workbench_sessions",
        "cptr_ssh",
        "cptr_chrome_browser",
        "cptr_delegate_task",
        "cptr_delegate_monitor",
    ):
        assert f'"{obsolete_mixed_tool}"' not in release

    names_block = re.search(r"MCP_COMPACT_TOOL_NAMES = \[(.*?)\] as const", release, re.S)
    assert names_block is not None
    names = re.findall(r'"([^"]+)"', names_block.group(1))
    assert len(names) == 26


def test_compact_read_surfaces_are_not_advertised_as_destructive_or_open_world():
    source = (MCP / "server" / "compact-gateways.ts").read_text(encoding="utf-8")

    for tool in (
        "cptr_workbench_sessions_read",
        "cptr_ssh_read",
        "cptr_chrome_read",
        "cptr_delegate_task_read",
        "cptr_delegate_monitor_read",
    ):
        pattern = rf'server\.registerTool\("{tool}", \{{.*?annotations: \{{ readOnlyHint: true, destructiveHint: false, openWorldHint: false \}}'
        assert re.search(pattern, source, re.S), tool


def test_compact_dangerous_control_surfaces_keep_conservative_safety_annotations():
    source = (MCP / "server" / "compact-gateways.ts").read_text(encoding="utf-8")

    expected = {
        "cptr_workbench_sessions_control": ("false", "true", "false"),
        "cptr_ssh_control": ("false", "true", "true"),
        "cptr_chrome_control": ("false", "true", "true"),
        "cptr_delegate_task_control": ("false", "true", "true"),
        "cptr_delegate_monitor_control": ("false", "true", "true"),
    }
    for tool, (read_only, destructive, open_world) in expected.items():
        annotation = (
            f"annotations: {{ readOnlyHint: {read_only}, destructiveHint: {destructive}, "
            f"openWorldHint: {open_world} }}"
        )
        pattern = rf'server\.registerTool\("{tool}", \{{.*?{re.escape(annotation)}'
        assert re.search(pattern, source, re.S), tool


def test_chatgpt_apps_ui_policy_is_persisted_for_future_maintainers():
    policy_path = ROOT / "AGENTS.md"
    assert policy_path.is_file(), "root AGENTS.md must preserve the ChatGPT Apps UI connector invariant"

    policy = policy_path.read_text(encoding="utf-8")
    assert "NON-NEGOTIABLE CHATGPT CONNECTOR INVARIANT" in policy
    assert "26-tool compact contract" in policy
    assert "ui://cptr/live-workbench.html" in policy
    assert "Exactly one production tool" in policy
    assert "legacy 63-core-tool / 69-registered-action surface remains regression-test-only" in policy
    assert "short-lived Workbench prompt ticket" in policy
    assert "explicit user instruction" in policy
