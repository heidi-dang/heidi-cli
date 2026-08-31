#!/usr/bin/env python3
"""Create or rotate the CPTR control token used only by Heidi's MCP service.

The raw token is printed once to stdout so the installer can capture it. Only a
SHA-256 digest is stored in CPTR. This script never writes the raw token to the
repository or CPTR database.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import secrets
import time
import uuid

from control_token_profiles import scopes_for_profile
from cptr.services.api_keys import list_api_keys, save_api_keys
from cptr.utils.config import get_or_create_user
from cptr.utils.db import init_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--name", default="heidi-mcp")
    parser.add_argument(
        "--profile",
        choices=("standard", "developer", "owner-full", "full"),
        default="owner-full",
        help="owner-full is the Heidi default and adds approved external execution plus confirmed managed-workspace deletion; developer adds only external execution; standard disables both; full is a legacy alias for owner-full",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    await init_db()
    user_id = await get_or_create_user(args.username)
    scopes = scopes_for_profile(args.profile)

    raw = f"sk-cptr-{secrets.token_urlsafe(32)}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    existing = await list_api_keys()
    retained = [
        key
        for key in existing
        if not (str(key.get("user_id")) == user_id and str(key.get("name")) == args.name)
    ]
    retained.append(
        {
            "id": str(uuid.uuid4()),
            "key_hash": digest,
            "user_id": user_id,
            "name": args.name,
            "scopes": scopes,
            "created_at": int(time.time()),
        }
    )
    await save_api_keys(retained)
    print(raw)


if __name__ == "__main__":
    asyncio.run(main())
