import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .auth_db import create_or_get_user_from_oauth, create_session, get_session, revoke_session
from .auth_encryption import (
    generate_state,
    generate_code_verifier,
    generate_code_challenge,
    encrypt_token,
)


GITHUB_CLIENT_ID = os.getenv("HEIDI_GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("HEIDI_GITHUB_CLIENT_SECRET", "")

CALLBACK_BASE_URL = os.getenv("HEIDI_CALLBACK_BASE_URL", "http://localhost:7777")

_states: Dict[str, Dict[str, Any]] = {}


def get_github_redirect_uri() -> str:
    """Get the OAuth callback URI."""
    return f"{CALLBACK_BASE_URL}/auth/callback/github"


def create_github_auth_url() -> tuple[str, str]:
    """Create GitHub OAuth URL with PKCE."""
    state = generate_state()
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    _states[state] = {"code_verifier": code_verifier, "created_at": datetime.utcnow()}

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": get_github_redirect_uri(),
        "scope": "read:user user:email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"https://github.com/login/oauth/authorize?{query}"

    return auth_url, state


def validate_state(state: str) -> bool:
    """Validate OAuth state."""
    if state not in _states:
        return False

    state_data = _states[state]
    created_at = state_data["created_at"]

    if datetime.utcnow() - created_at > timedelta(minutes=10):
        del _states[state]
        return False

    return True


def get_code_verifier(state: str) -> Optional[str]:
    """Get code verifier for state."""
    return _states.get(state, {}).get("code_verifier")


def cleanup_state(state: str) -> None:
    """Remove state after use."""
    if state in _states:
        del _states[state]


async def exchange_code_for_token(code: str, state: str) -> Optional[Dict[str, Any]]:
    """Exchange OAuth code for access token."""
    if not validate_state(state):
        return None

    code_verifier = get_code_verifier(state)
    if not code_verifier:
        return None

    cleanup_state(state)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": get_github_redirect_uri(),
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        return None

    return response.json()


async def get_github_user(access_token: str) -> Optional[Dict[str, Any]]:
    """Get GitHub user info."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

    if response.status_code != 200:
        return None

    return response.json()


async def get_github_emails(access_token: str) -> list[Dict[str, Any]]:
    """Get GitHub user emails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

    if response.status_code != 200:
        return []

    return response.json()


async def complete_github_login(code: str, state: str) -> Optional[Dict[str, Any]]:
    """Complete GitHub OAuth login."""
    token_data = await exchange_code_for_token(code, state)
    if not token_data:
        return None

    access_token = token_data.get("access_token")
    if not access_token:
        return None

    user_data = await get_github_user(access_token)
    if not user_data:
        return None

    email = user_data.get("email")
    if not email:
        emails = await get_github_emails(access_token)
        primary_emails = [e for e in emails if e.get("primary")]
        if primary_emails:
            email = primary_emails[0].get("email")

    name = user_data.get("name") or user_data.get("login") or "User"
    avatar_url = user_data.get("avatar_url")
    provider_user_id = str(user_data.get("id"))

    expires_in = token_data.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    refresh_token = token_data.get("refresh_token")
    access_token_encrypted = encrypt_token(access_token)
    refresh_token_encrypted = encrypt_token(refresh_token) if refresh_token else None

    user = create_or_get_user_from_oauth(
        provider="github",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        access_token=access_token_encrypted,
        refresh_token=refresh_token_encrypted,
        token_expires_at=token_expires_at,
    )

    session = create_session(user.id)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat(),
        },
        "session_id": session.id,
    }


def logout_session(session_id: str) -> bool:
    """Logout by revoking session."""
    session = get_session(session_id)
    if not session:
        return False

    revoke_session(session_id)
    return True
