import sqlite3
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


def get_db_path() -> Path:
    from .config import ConfigManager

    ConfigManager.ensure_dirs()
    return ConfigManager.heidi_dir() / "heidi.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT,
            name TEXT NOT NULL,
            avatar_url TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,
            token_expires_at TEXT,
            UNIQUE(provider, provider_user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_id ON oauth_accounts(user_id)
    """)

    conn.commit()
    conn.close()


def generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    random_part = secrets.token_hex(8)
    return f"{prefix}_{random_part}"


@dataclass
class User:
    id: str
    email: Optional[str]
    name: str
    avatar_url: Optional[str]
    created_at: datetime


@dataclass
class OAuthAccount:
    id: str
    user_id: str
    provider: str
    provider_user_id: str
    access_token_encrypted: Optional[str]
    refresh_token_encrypted: Optional[str]
    token_expires_at: Optional[datetime]


@dataclass
class Session:
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]


def create_user(email: Optional[str], name: str, avatar_url: Optional[str] = None) -> User:
    """Create a new user."""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = generate_id("usr")
    created_at = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO users (id, email, name, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, email, name, avatar_url, created_at),
    )

    conn.commit()
    conn.close()

    return User(
        id=user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        created_at=datetime.fromisoformat(created_at),
    )


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        avatar_url=row["avatar_url"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def get_user_by_provider(provider: str, provider_user_id: str) -> Optional[User]:
    """Get user by OAuth provider."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT users.* FROM users
        JOIN oauth_accounts ON users.id = oauth_accounts.user_id
        WHERE oauth_accounts.provider = ? AND oauth_accounts.provider_user_id = ?
    """,
        (provider, provider_user_id),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        avatar_url=row["avatar_url"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def create_or_get_user_from_oauth(
    provider: str,
    provider_user_id: str,
    email: Optional[str],
    name: str,
    avatar_url: Optional[str] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_expires_at: Optional[datetime] = None,
) -> User:
    """Create or update user from OAuth."""
    existing_user = get_user_by_provider(provider, provider_user_id)

    if existing_user:
        conn = get_connection()
        cursor = conn.cursor()

        if email and not existing_user.email:
            cursor.execute("UPDATE users SET email = ? WHERE id = ?", (email, existing_user.id))

        cursor.execute(
            """
            INSERT OR REPLACE INTO oauth_accounts 
            (id, user_id, provider, provider_user_id, access_token_encrypted, refresh_token_encrypted, token_expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                generate_id("oauth"),
                existing_user.id,
                provider,
                provider_user_id,
                access_token,
                refresh_token,
                token_expires_at.isoformat() if token_expires_at else None,
            ),
        )

        conn.commit()
        conn.close()
        return existing_user

    conn = get_connection()
    cursor = conn.cursor()

    user = create_user(email, name, avatar_url)

    cursor.execute(
        """
        INSERT INTO oauth_accounts 
        (id, user_id, provider, provider_user_id, access_token_encrypted, refresh_token_encrypted, token_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            generate_id("oauth"),
            user.id,
            provider,
            provider_user_id,
            access_token,
            refresh_token,
            token_expires_at.isoformat() if token_expires_at else None,
        ),
    )

    conn.commit()
    conn.close()

    return user


def create_session(user_id: str, expires_in_days: int = 7) -> Session:
    """Create a new session."""
    conn = get_connection()
    cursor = conn.cursor()

    session_id = generate_id("sess")
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=expires_in_days)

    cursor.execute(
        """
        INSERT INTO sessions (id, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """,
        (session_id, user_id, created_at.isoformat(), expires_at.isoformat()),
    )

    conn.commit()
    conn.close()

    return Session(
        id=session_id,
        user_id=user_id,
        created_at=created_at,
        expires_at=expires_at,
        revoked_at=None,
    )


def get_session(session_id: str) -> Optional[Session]:
    """Get valid session by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM sessions 
        WHERE id = ? AND revoked_at IS NULL AND expires_at > ?
    """,
        (session_id, datetime.utcnow().isoformat()),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return Session(
        id=row["id"],
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
        revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
    )


def revoke_session(session_id: str) -> None:
    """Revoke a session."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE sessions SET revoked_at = ? WHERE id = ?
    """,
        (datetime.utcnow().isoformat(), session_id),
    )

    conn.commit()
    conn.close()


def cleanup_expired_sessions() -> int:
    """Remove expired sessions. Returns count of removed sessions."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM sessions WHERE expires_at < ?
    """,
        (datetime.utcnow().isoformat(),),
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted
