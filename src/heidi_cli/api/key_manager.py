"""
Heidi API Key Manager

Generates and manages custom API keys for unified model access.
Users get a single Heidi API key that works across all model providers.
"""

import uuid
import hashlib
import secrets
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3
from dataclasses import dataclass, asdict

from ..shared.config import ConfigLoader
from ..runtime.db import db


@dataclass
class APIKey:
    """Represents a Heidi API key with metadata."""
    key_id: str
    api_key: str
    name: str
    user_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    rate_limit: int  # requests per minute
    usage_count: int = 0
    last_used: Optional[datetime] = None
    permissions: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["read", "write"]
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid and active."""
        return self.is_active and not self.is_expired


class APIKeyManager:
    """Manages Heidi API keys for unified model access."""
    
    def __init__(self):
        self.config = ConfigLoader.load()
        self._init_database()
    
    def _init_database(self):
        """Initialize the API keys database table."""
        with db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    rate_limit INTEGER NOT NULL DEFAULT 100,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    last_used TEXT,
                    permissions TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)")
            
            conn.commit()
    
    def generate_api_key(
        self, 
        name: str,
        user_id: str,
        expires_days: Optional[int] = None,
        rate_limit: int = 100,
        permissions: List[str] = None
    ) -> APIKey:
        """Generate a new Heidi API key."""
        
        # Generate unique key
        key_id = str(uuid.uuid4())
        raw_key = f"heidik_{secrets.token_urlsafe(32)}"
        api_key = self._hash_api_key(raw_key)
        
        # Set expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # Create API key object
        api_key_obj = APIKey(
            key_id=key_id,
            api_key=api_key,
            name=name,
            user_id=user_id,
            created_at=datetime.now(),
            expires_at=expires_at,
            is_active=True,
            rate_limit=rate_limit,
            permissions=permissions or ["read", "write"]
        )
        
        # Store in database
        self._store_api_key(api_key_obj)
        
        # Return with raw key (only shown once)
        api_key_obj.api_key = raw_key
        return api_key_obj
    
    def _hash_api_key(self, raw_key: str) -> str:
        """Hash the API key for secure storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _store_api_key(self, api_key: APIKey):
        """Store API key in database."""
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO api_keys (
                    key_id, api_key, name, user_id, created_at, expires_at,
                    is_active, rate_limit, usage_count, last_used, permissions, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api_key.key_id,
                api_key.api_key,  # hashed
                api_key.name,
                api_key.user_id,
                api_key.created_at.isoformat(),
                api_key.expires_at.isoformat() if api_key.expires_at else None,
                1 if api_key.is_active else 0,
                api_key.rate_limit,
                api_key.usage_count,
                api_key.last_used.isoformat() if api_key.last_used else None,
                json.dumps(api_key.permissions),
                json.dumps(api_key.metadata)
            ))
            conn.commit()
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key object if valid."""
        hashed_key = self._hash_api_key(api_key)
        
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM api_keys 
                WHERE api_key = ? AND is_active = 1
            """, (hashed_key,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert to APIKey object
            api_key_obj = APIKey(
                key_id=row['key_id'],
                api_key=hashed_key,
                name=row['name'],
                user_id=row['user_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                is_active=bool(row['is_active']),
                rate_limit=row['rate_limit'],
                usage_count=row['usage_count'],
                last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
                permissions=json.loads(row['permissions']),
                metadata=json.loads(row['metadata'])
            )
            
            # Check if expired
            if api_key_obj.is_expired:
                return None
            
            # Update usage stats
            self._update_usage(api_key_obj.key_id)
            
            return api_key_obj
    
    def _update_usage(self, key_id: str):
        """Update usage statistics for an API key."""
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE api_keys 
                SET usage_count = usage_count + 1, 
                    last_used = ?
                WHERE key_id = ?
            """, (datetime.now().isoformat(), key_id))
            conn.commit()
    
    def list_api_keys(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM api_keys 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            keys = []
            for row in cursor.fetchall():
                api_key_obj = APIKey(
                    key_id=row['key_id'],
                    api_key=row['api_key'],  # hashed
                    name=row['name'],
                    user_id=row['user_id'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    is_active=bool(row['is_active']),
                    rate_limit=row['rate_limit'],
                    usage_count=row['usage_count'],
                    last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
                    permissions=json.loads(row['permissions']),
                    metadata=json.loads(row['metadata'])
                )
                keys.append(api_key_obj)
            
            return keys
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        with db.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE api_keys 
                SET is_active = 0 
                WHERE key_id = ?
            """, (key_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_usage_stats(self, key_id: str) -> Dict:
        """Get usage statistics for an API key."""
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT usage_count, last_used, created_at 
                FROM api_keys 
                WHERE key_id = ?
            """, (key_id,))
            
            row = cursor.fetchone()
            if not row:
                return {}
            
            created_at = datetime.fromisoformat(row['created_at'])
            last_used = datetime.fromisoformat(row['last_used']) if row['last_used'] else None
            
            return {
                "usage_count": row['usage_count'],
                "created_at": created_at,
                "last_used": last_used,
                "days_active": (datetime.now() - created_at).days,
                "avg_daily_usage": row['usage_count'] / max(1, (datetime.now() - created_at).days)
            }


# Global instance
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
