import os
import hashlib
from cryptography.fernet import Fernet
from typing import Optional


def get_encryption_key() -> bytes:
    """Get or create encryption key."""
    from .config import ConfigManager

    key_file = ConfigManager.heidi_dir() / ".key"

    if key_file.exists():
        with open(key_file, "rb") as f:
            return f.read()

    key = Fernet.generate_key()
    key_file.write_bytes(key)
    os.chmod(key_file, 0o600)

    return key


def encrypt_token(token: str) -> str:
    """Encrypt an OAuth token."""
    if not token:
        return ""
    f = Fernet(get_encryption_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> Optional[str]:
    """Decrypt an OAuth token."""
    if not encrypted:
        return None
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return None


def generate_state() -> str:
    """Generate a random state for OAuth."""
    import secrets

    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    """Generate PKCE code verifier."""
    import secrets

    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    import base64

    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")
