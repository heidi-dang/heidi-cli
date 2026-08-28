#!/usr/bin/env python3
"""Create/read the secret handoff between Heidi split backend and MCP installs."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "heidi.split-handoff.v1"


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def create(args: argparse.Namespace) -> int:
    data = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend_hostname": args.hostname,
        "tailscale_ipv4": args.tailscale_ipv4,
        "tailscale_dns": args.tailscale_dns,
        "cptr_private_url": args.cptr_url.rstrip("/"),
        "cptr_api_token": args.cptr_api_token,
        "cptr_api_revision": args.cptr_api_revision,
        "fdx_version": args.fdx_version,
        "fdx_protocol": args.fdx_protocol,
        "compatibility_version": args.compatibility_version,
    }
    path = Path(args.output).expanduser()
    _atomic_write(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"Split handoff file: {path}")
    print("WARNING: this report contains a scoped CPTR credential. Keep it private and delete copied versions after the MCP server is configured.")
    print("\n================ HEIDI SPLIT HANDOFF REPORT ================")
    print(f"Backend host:          {data['backend_hostname']}")
    print(f"Tailscale IPv4:        {data['tailscale_ipv4']}")
    print(f"Tailscale DNS:         {data['tailscale_dns']}")
    print(f"CPTR private URL:      {data['cptr_private_url']}")
    print(f"CPTR API token:        {data['cptr_api_token']}")
    print(f"CPTR API revision:     {data['cptr_api_revision']}")
    print(f"FDX version:           {data['fdx_version']}")
    print(f"FDX protocol:          {data['fdx_protocol']}")
    print(f"Compatibility:         {data['compatibility_version']}")
    print("============================================================")
    print("\nOn the MCP server:")
    print("  git clone https://github.com/heidi-dang/heidi-cli.git")
    print("  cd heidi-cli")
    print("  ./scripts/install-split-mcp.sh")
    print("\nWhen prompted, use the CPTR private URL and CPTR API token above, or securely transfer the JSON handoff file and provide its path.")
    return 0


def read(args: argparse.Namespace) -> int:
    path = Path(args.input).expanduser()
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        raise SystemExit(f"handoff file not found: {path}")
    if mode & 0o077:
        raise SystemExit(f"handoff file must not be group/world accessible: {path} mode={mode:o}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"unsupported handoff schema: {data.get('schema')!r}")
    if args.field:
        value = data.get(args.field)
        if value is None:
            raise SystemExit(f"missing field: {args.field}")
        print(value)
    else:
        safe = dict(data)
        if "cptr_api_token" in safe:
            safe["cptr_api_token"] = "<redacted>"
        print(json.dumps(safe, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("create")
    make.add_argument("--output", required=True)
    make.add_argument("--hostname", required=True)
    make.add_argument("--tailscale-ipv4", required=True)
    make.add_argument("--tailscale-dns", default="")
    make.add_argument("--cptr-url", required=True)
    make.add_argument("--cptr-api-token", required=True)
    make.add_argument("--cptr-api-revision", default="v1")
    make.add_argument("--fdx-version", required=True)
    make.add_argument("--fdx-protocol", default="2")
    make.add_argument("--compatibility-version", required=True)
    make.set_defaults(func=create)

    show = sub.add_parser("read")
    show.add_argument("--input", required=True)
    show.add_argument("--field")
    show.set_defaults(func=read)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
