"""
Security and Authentication system for model hosting.
"""

from __future__ import annotations

import hashlib
import hmac
import jwt
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import sqlite3
import logging

logger = logging.getLogger("heidi.security")

@dataclass
class User:
    """User account."""
    id: str
    username: str
    email: str
    api_key: str
    created_at: datetime
    last_active: Optional[datetime] = None
    is_active: bool = True
    tier: str = "basic"  # basic, premium, enterprise
    rate_limit_rpm: int = 60  # requests per minute
    rate_limit_tpm: int = 10000  # tokens per minute
    allowed_models: List[str] = None
    
    def __post_init__(self):
        if self.allowed_models is None:
            self.allowed_models = []

@dataclass
class APIKey:
    """API key information."""
    key_id: str
    user_id: str
    key_hash: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

@dataclass
class RateLimitInfo:
    """Rate limiting information."""
    requests_per_minute: int
    tokens_per_minute: int
    current_requests: int = 0
    current_tokens: int = 0
    window_start: datetime = None
    
    def __post_init__(self):
        if self.window_start is None:
            self.window_start = datetime.now(timezone.utc)

class SecurityManager:
    """Manages authentication, authorization, and rate limiting."""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("state/security.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jwt_secret = secrets.token_urlsafe(32)
        self._init_database()
        
        # Rate limiting cache (in production, use Redis)
        self._rate_limits: Dict[str, RateLimitInfo] = {}
    
    def _init_database(self):
        """Initialize security database."""
        with sqlite3.connect(self.db_path) as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    tier TEXT DEFAULT 'basic',
                    rate_limit_rpm INTEGER DEFAULT 60,
                    rate_limit_tpm INTEGER DEFAULT 10000,
                    allowed_models TEXT
                )
            """)
            
            # API keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    permissions TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Session table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Audit log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)
            
            conn.commit()
    
    def create_user(self, username: str, email: str, tier: str = "basic") -> User:
        """Create a new user."""
        user_id = secrets.token_urlsafe(16)
        api_key = f"hd_{secrets.token_urlsafe(32)}"
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            api_key=api_key,
            created_at=datetime.now(timezone.utc),
            tier=tier,
            rate_limit_rpm=self._get_tier_limits(tier)["rpm"],
            rate_limit_tpm=self._get_tier_limits(tier)["tpm"]
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO users (
                    id, username, email, api_key, created_at, tier,
                    rate_limit_rpm, rate_limit_tpm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id, user.username, user.email, user.api_key,
                user.created_at.isoformat(), user.tier,
                user.rate_limit_rpm, user.rate_limit_tpm
            ))
            conn.commit()
        
        self._log_action(
            user_id=user.id,
            action="user_created",
            resource=f"user:{user.id}",
            details={"username": username, "email": email, "tier": tier}
        )
        
        return user
    
    def authenticate_request(self, api_key: str, ip_address: str = None) -> Optional[User]:
        """Authenticate a request via API key."""
        try:
            user = self._get_user_by_api_key(api_key)
            if not user or not user.is_active:
                self._log_action(
                    action="auth_failed",
                    resource="api_key",
                    details={"reason": "invalid_key" if not user else "inactive_user"},
                    ip_address=ip_address
                )
                return None
            
            # Update last active
            self._update_user_activity(user.id)
            
            self._log_action(
                user_id=user.id,
                action="auth_success",
                resource="api_key",
                ip_address=ip_address
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._log_action(
                action="auth_error",
                resource="api_key",
                details={"error": str(e)},
                ip_address=ip_address
            )
            return None
    
    def validate_model_access(self, user: User, model_id: str) -> bool:
        """Check if user can access specific model."""
        if not user.allowed_models:
            # No restrictions - can access all models
            return True
        
        return model_id in user.allowed_models
    
    def check_rate_limit(self, user: User, request_tokens: int = 0) -> Tuple[bool, str]:
        """Check if user is within rate limits."""
        now = datetime.now(timezone.utc)
        user_key = user.id
        
        # Get or create rate limit info
        if user_key not in self._rate_limits:
            self._rate_limits[user_key] = RateLimitInfo(
                requests_per_minute=user.rate_limit_rpm,
                tokens_per_minute=user.rate_limit_tpm
            )
        
        rate_info = self._rate_limits[user_key]
        
        # Reset window if needed
        if now - rate_info.window_start > timedelta(minutes=1):
            rate_info.current_requests = 0
            rate_info.current_tokens = 0
            rate_info.window_start = now
        
        # Check request limit
        if rate_info.current_requests >= rate_info.requests_per_minute:
            return False, "Rate limit exceeded: too many requests"
        
        # Check token limit
        if rate_info.current_tokens + request_tokens > rate_info.tokens_per_minute:
            return False, "Rate limit exceeded: too many tokens"
        
        # Update counters
        rate_info.current_requests += 1
        rate_info.current_tokens += request_tokens
        
        return True, "OK"
    
    def create_api_key(self, user_id: str, name: str, permissions: List[str], 
                      expires_days: Optional[int] = None) -> APIKey:
        """Create a new API key for user."""
        key_id = secrets.token_urlsafe(16)
        api_key = f"hd_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_api_key(api_key)
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        api_key_obj = APIKey(
            key_id=key_id,
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_keys (
                    key_id, user_id, key_hash, name, permissions,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                api_key_obj.key_id, api_key_obj.user_id, api_key_obj.key_hash,
                api_key_obj.name, json.dumps(permissions),
                api_key_obj.created_at.isoformat(),
                api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None
            ))
            conn.commit()
        
        self._log_action(
            user_id=user_id,
            action="api_key_created",
            resource=f"api_key:{key_id}",
            details={"name": name, "permissions": permissions}
        )
        
        return api_key_obj
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE api_keys SET is_active = 0 WHERE key_id = ?
            """, (key_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                self._log_action(
                    action="api_key_revoked",
                    resource=f"api_key:{key_id}"
                )
                return True
            return False
    
    def list_user_api_keys(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM api_keys WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))
            
            keys = []
            for row in cursor.fetchall():
                keys.append(APIKey(
                    key_id=row['key_id'],
                    user_id=row['user_id'],
                    key_hash=row['key_hash'],
                    name=row['name'],
                    permissions=json.loads(row['permissions']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
                    is_active=row['is_active']
                ))
            
            return keys
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Get user info
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            user_row = cursor.fetchone()
            
            if not user_row:
                return {}
            
            # Get API key count
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM api_keys WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            key_count = cursor.fetchone()['count']
            
            # Get recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM audit_log 
                WHERE user_id = ? AND timestamp > datetime('now', '-24 hours')
            """, (user_id,))
            recent_activity = cursor.fetchone()['count']
            
            return {
                "user_id": user_id,
                "username": user_row['username'],
                "email": user_row['email'],
                "tier": user_row['tier'],
                "is_active": user_row['is_active'],
                "created_at": user_row['created_at'],
                "last_active": user_row['last_active'],
                "rate_limits": {
                    "requests_per_minute": user_row['rate_limit_rpm'],
                    "tokens_per_minute": user_row['rate_limit_tpm']
                },
                "api_key_count": key_count,
                "recent_activity_24h": recent_activity
            }
    
    def _get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM users WHERE api_key = ? AND is_active = 1
            """, (api_key,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                api_key=row['api_key'],
                created_at=datetime.fromisoformat(row['created_at']),
                last_active=datetime.fromisoformat(row['last_active']) if row['last_active'] else None,
                is_active=row['is_active'],
                tier=row['tier'],
                rate_limit_rpm=row['rate_limit_rpm'],
                rate_limit_tpm=row['rate_limit_tpm'],
                allowed_models=json.loads(row['allowed_models']) if row['allowed_models'] else []
            )
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _get_tier_limits(self, tier: str) -> Dict[str, int]:
        """Get rate limits for user tier."""
        limits = {
            "basic": {"rpm": 60, "tpm": 10000},
            "premium": {"rpm": 300, "tpm": 50000},
            "enterprise": {"rpm": 1000, "tpm": 200000}
        }
        return limits.get(tier, limits["basic"])
    
    def _update_user_activity(self, user_id: str):
        """Update user's last activity timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET last_active = ? WHERE id = ?
            """, (datetime.now(timezone.utc).isoformat(), user_id))
            conn.commit()
    
    def _log_action(self, action: str, resource: str, user_id: str = None,
                   session_id: str = None, details: Dict = None,
                   ip_address: str = None, user_agent: str = None):
        """Log security action."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_log (
                        timestamp, user_id, session_id, action, resource,
                        details, ip_address, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    user_id, session_id, action, resource,
                    json.dumps(details) if details else None,
                    ip_address, user_agent
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")


# Global security manager instance
_security_manager: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
