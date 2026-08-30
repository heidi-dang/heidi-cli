"""Dependency-free Heidi control-token profile policy.

This module intentionally has no CPTR imports so installer and release CI can
validate capability policy without bootstrapping the backend runtime.
"""

from __future__ import annotations


STANDARD_SCOPES = [
    "workspace:read",
    "workspace:provision",
    "task:read",
    "task:write",
    "autonomous:run",
    "git:read",
    "coding:read",
    "coding:write",
    "command:execute",
]
DEVELOPER_SCOPES = ["command:external"]
OWNER_FULL_SCOPES = [*DEVELOPER_SCOPES, "workspace:delete"]


def normalize_profile(profile: str) -> str:
    """Return the canonical profile name, accepting legacy ``full``."""
    value = profile.strip().lower()
    if value == "full":
        return "owner-full"
    if value not in {"standard", "developer", "owner-full"}:
        raise ValueError(f"unsupported control profile: {profile}")
    return value


def scopes_for_profile(profile: str) -> list[str]:
    """Return a fresh ordered scope list for a canonical or legacy profile."""
    normalized = normalize_profile(profile)
    scopes = [*STANDARD_SCOPES]
    if normalized == "developer":
        scopes.extend(DEVELOPER_SCOPES)
    elif normalized == "owner-full":
        scopes.extend(OWNER_FULL_SCOPES)
    return scopes
