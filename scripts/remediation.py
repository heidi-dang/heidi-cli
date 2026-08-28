#!/usr/bin/env python3
"""Generate safe, copy-ready AI repair prompts for Heidi verification failures."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SENSITIVE = re.compile(r"(?i)(token|secret|password|authorization|cookie|api[_-]?key|credential)")

TEMPLATES = {
    "tailscale": """Repair the Heidi CLI split-deployment Tailscale path. Inspect Tailscale service/status, this machine's tailnet identity/IP, routing/firewall/listen address, and reachability to the peer. Do not expose CPTR publicly and do not disable host-key/TLS/authentication safeguards. Restore private connectivity, then prove it with tailscale status plus an authenticated CPTR readiness/control request from the MCP side.""",
    "cptr_health": """Repair the Heidi CPTR backend. Inspect the installed Heidi release, systemd service, environment names (never print secret values), process/listener state, CPTR logs, database/migrations, Python environment, FDX configuration, and /api/health/live + /api/health/ready. Fix the root cause without deleting ~/.cptr. Prove both health endpoints pass and the service survives restart.""",
    "cptr_auth": """Repair the Heidi MCP→CPTR authenticated control path. Inspect the scoped Heidi MCP control credential configuration, CPTR control-auth store, service environment names/permissions, CPTR_BASE_URL, and Tailscale/private network reachability if split mode is used. Never print the credential. Rotate only the Heidi MCP credential if needed. Prove an authenticated /api/control/v1/workspaces request returns HTTP 200.""",
    "fdx": """Repair Heidi FDX integration. Inspect the installed fdx binary/version, resident daemon protocol negotiation, CPTR FDX environment, repository containment, daemon logs/errors, and compatibility manifest. Rebuild/reinstall only the compatible Heidi FDX artifact if needed. Prove `fdx --version`, protocol compatibility, and one structured resident read/search through CPTR all pass.""",
    "mcp_health": """Repair the Heidi ChatGPT MCP service. Inspect the installed release, Node runtime, systemd unit, loopback listener, owner/group and environment-file permissions, MCP logs, Workbench assets, and /health. Do not expose CPTR directly. Prove local MCP /health passes after restart.""",
    "mcp_contract": """Repair the Heidi MCP contract mismatch. Compare the installed compatibility manifest, MCP package/contract version, registered action count/names, Workbench resource, and deployed-contract checker. Do not weaken tool safety annotations or allow:delegate enforcement. Rebuild/redeploy the matching release and prove the exact expected MCP contract passes.""",
    "cloudflare": """Repair the Heidi Cloudflare MCP edge. Inspect DNS record/proxy state, selected transport (Caddy origin or Cloudflare Tunnel), Cloudflare Access MCP application, Managed OAuth/DCR, allowed redirect URIs, Access policy, issuer/audience/JWKS, TLS, and origin reachability. Use the user's Cloudflare API token only if explicitly provided; never print or persist it. Prove the public MCP edge is reachable and Access/OAuth metadata is coherent.""",
    "caddy": """Repair the Heidi Caddy public MCP origin. Inspect Caddy installation/version, systemd service, Caddyfile syntax, public hostname, reverse_proxy target, TLS issuance, ports 80/443, and Cloudflare proxy compatibility. Keep MCP bound to loopback behind Caddy. Prove `caddy validate`, HTTPS /health reachability, and MCP local health all pass.""",
    "systemd": """Repair the Heidi systemd deployment. Inspect unit files, EnvironmentFile paths/permissions, users/groups, WorkingDirectory/ExecStart, restart policy, dependency ordering, logs, and enabled/active state. Preserve versioned releases and do not delete CPTR data. Prove all required Heidi services are enabled, active, restart cleanly, and pass their health checks.""",
    "dependency": """Repair missing/incompatible Heidi runtime dependencies. Use the compatibility/release manifest as authority. Install only supported pinned/verified runtimes, verify checksums/signatures, rebuild the affected component, and rerun its focused tests plus Heidi verification. Do not bypass signature/checksum verification.""",
    "compatibility": """Repair a Heidi component compatibility mismatch. Treat release/compatibility.json as the source of truth for MCP contract, CPTR API revision, FDX protocol, runtime requirements, and migrations. Install one coherent Heidi release rather than mixing component versions. Preserve ~/.cptr and take a backup before migrations. Prove the compatibility check and full stack verification pass.""",
    "backup": """Repair Heidi backup/restore readiness. Inspect the configured backup directory, age recipient/key availability, filesystem permissions/free space, CPTR data path, archive creation, encryption, checksum, and restore validation. Never output private keys or plaintext backup content. Prove an encrypted backup can be created and structurally validated.""",
    "generic": """Repair the failed Heidi CLI verification checks. Inspect only the components implicated by the evidence below, find the root cause, implement a durable fix, and rerun Heidi's focused checks followed by `heidi verify`. Never print or commit secrets, never delete ~/.cptr, and never weaken authentication/sandbox/network safety to make a check pass.""",
}


def redact(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if SENSITIVE.search(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"\bsk-cptr-[A-Za-z0-9_-]+\b", "<redacted-cptr-token>", value)
        value = re.sub(r"(?i)Bearer\s+\S+", "Bearer <redacted>", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", choices=sorted(TEMPLATES), default="generic")
    parser.add_argument("--failure", required=True)
    parser.add_argument("--topology", default="unknown")
    parser.add_argument("--role", default="unknown")
    parser.add_argument("--details-json")
    parser.add_argument("--details-file")
    args = parser.parse_args()

    details = {}
    if args.details_json:
        details = json.loads(args.details_json)
    elif args.details_file:
        details = json.loads(Path(args.details_file).read_text(encoding="utf-8"))
    details = redact(details)

    print("Copy this prompt into ChatGPT/Codex/Claude or another trusted engineering agent:\n")
    print("--- BEGIN HEIDI AI REPAIR PROMPT ---")
    print("You are repairing a Heidi CLI deployment. Finish the repair to production quality; do not merely explain commands.")
    print(f"Deployment topology: {args.topology}")
    print(f"Machine role: {args.role}")
    print(f"Failed verification: {args.failure}")
    print(TEMPLATES[args.category])
    if details:
        print("\nSafe diagnostics already collected (secret values redacted):")
        print(json.dumps(details, indent=2, sort_keys=True))
    print("\nAcceptance evidence required before you say done:")
    print("1. Identify the root cause and changed files/configuration.")
    print("2. Show the focused failing check now passing.")
    print("3. Run `heidi verify` and show the final PASS summary.")
    print("4. Run `heidi doctor` and report any remaining warnings.")
    print("5. Confirm no secret values were printed/committed and no safety control was disabled.")
    print("6. If a repair cannot be completed automatically, state the single user-only action still required and why.")
    print("--- END HEIDI AI REPAIR PROMPT ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
