#!/usr/bin/env python3
"""Verify cross-component Heidi release compatibility from canonical sources."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOOL_LIST_RE = re.compile(
    r"export\s+const\s+MCP_COMPACT_TOOL_NAMES\s*=\s*\[(?P<body>.*?)\]\s*as\s+const\s*;",
    re.DOTALL,
)
QUOTED_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"]+)"')


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_tool_names(root: Path) -> list[str]:
    release_source = (root / "apps/mcp/server/release.ts").read_text(encoding="utf-8")
    match = TOOL_LIST_RE.search(release_source)
    if match is None:
        raise ValueError("MCP_COMPACT_TOOL_NAMES canonical inventory is missing")
    names = [bytes(value, "utf-8").decode("unicode_escape") for value in QUOTED_RE.findall(match.group("body"))]
    if not names:
        raise ValueError("MCP_COMPACT_TOOL_NAMES canonical inventory is empty")
    if len(names) != len(set(names)):
        raise ValueError("MCP_COMPACT_TOOL_NAMES contains duplicate tools")
    if "export const MCP_CONTRACT_TOOL_COUNT = MCP_COMPACT_TOOL_NAMES.length;" not in release_source:
        raise ValueError("MCP_CONTRACT_TOOL_COUNT must derive from MCP_COMPACT_TOOL_NAMES.length")
    return names


def verify(root: Path, expected_version: str | None = None) -> dict[str, object]:
    root = root.resolve()
    compatibility = _json(root / "release/compatibility.json")
    package = _json(root / "package.json")
    mcp_package = _json(root / "apps/mcp/package.json")
    cptr_source = (root / "apps/cptr/pyproject.toml").read_text(encoding="utf-8")
    fdx_source = (root / "crates/fdx/Cargo.toml").read_text(encoding="utf-8")
    cptr_match = VERSION_RE.search(cptr_source)
    fdx_match = VERSION_RE.search(fdx_source)
    if cptr_match is None or fdx_match is None:
        raise ValueError("CPTR or FDX package version is missing")

    heidi_version = str(package["version"])
    versions = {
        "root Heidi version": heidi_version,
        "compatibility Heidi version": str(compatibility["heidi_version"]),
        "MCP contract version": str(compatibility["mcp"]["contract_version"]),
        "MCP package version": str(mcp_package["version"]),
    }
    target = expected_version or heidi_version
    mismatches = [f"{label} {actual} != {target}" for label, actual in versions.items() if actual != target]
    if mismatches:
        raise ValueError("; ".join(mismatches))

    cptr_version = cptr_match.group(1)
    fdx_version = fdx_match.group(1)
    if str(compatibility["cptr"]["package_version"]) != cptr_version:
        raise ValueError("CPTR compatibility version does not match apps/cptr/pyproject.toml")
    if str(compatibility["fdx"]["package_version"]) != fdx_version:
        raise ValueError("FDX compatibility version does not match crates/fdx/Cargo.toml")

    tools = compact_tool_names(root)
    registered_count = int(compatibility["mcp"]["registered_action_count"])
    if registered_count != len(tools):
        raise ValueError(
            f"MCP compatibility action count {registered_count} != canonical runtime inventory {len(tools)}"
        )
    if "cptr_workspace_lifecycle" not in tools:
        raise ValueError("v2.1 canonical MCP inventory is missing cptr_workspace_lifecycle")
    if int(compatibility["fdx"]["protocol_version"]) != 2:
        raise ValueError("FDX protocol compatibility must remain 2")

    return {
        "heidi_version": heidi_version,
        "mcp_tool_count": len(tools),
        "cptr_version": cptr_version,
        "fdx_version": fdx_version,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    result = verify(args.root, args.expected_version)
    print(
        "compatibility-contract=PASS "
        f"heidi={result['heidi_version']} mcp_tools={result['mcp_tool_count']} "
        f"cptr={result['cptr_version']} fdx={result['fdx_version']}"
    )


if __name__ == "__main__":
    main()
