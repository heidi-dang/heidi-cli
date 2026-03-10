"""
Heidi API Authentication

Handles authentication and authorization for Heidi API keys.
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .key_manager import get_api_key_manager, APIKey
from ..integrations.analytics import UsageAnalytics


@dataclass
class AuthResult:
    """Result of API key authentication."""
    success: bool
    api_key: Optional[APIKey] = None
    error_message: Optional[str] = None
    rate_limited: bool = False


class HeidiAuthenticator:
    """Authenticates Heidi API keys and enforces rate limits."""
    
    def __init__(self):
        self.key_manager = get_api_key_manager()
        self.analytics = UsageAnalytics()
        self._rate_limit_cache: Dict[str, Dict] = {}
    
    def authenticate(self, api_key: str, request_info: Dict = None) -> AuthResult:
        """Authenticate an API key and check rate limits."""
        
        # Validate API key
        key_obj = self.key_manager.validate_api_key(api_key)
        if not key_obj:
            return AuthResult(
                success=False,
                error_message="Invalid or expired API key"
            )
        
        # Check rate limits
        if self._is_rate_limited(key_obj):
            return AuthResult(
                success=False,
                api_key=key_obj,
                error_message="Rate limit exceeded",
                rate_limited=True
            )
        
        # Record successful authentication
        self._record_auth_success(key_obj, request_info)
        
        return AuthResult(
            success=True,
            api_key=key_obj
        )
    
    def _is_rate_limited(self, api_key: APIKey) -> bool:
        """Check if the API key is rate limited."""
        current_time = time.time()
        key_id = api_key.key_id
        
        # Get or create rate limit entry
        if key_id not in self._rate_limit_cache:
            self._rate_limit_cache[key_id] = {
                "requests": [],
                "last_cleanup": current_time
            }
        
        rate_info = self._rate_limit_cache[key_id]
        
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - 60
        rate_info["requests"] = [
            req_time for req_time in rate_info["requests"] 
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(rate_info["requests"]) >= api_key.rate_limit:
            return True
        
        # Add current request
        rate_info["requests"].append(current_time)
        
        # Cleanup old entries periodically
        if current_time - rate_info["last_cleanup"] > 300:  # 5 minutes
            self._cleanup_rate_limits()
            rate_info["last_cleanup"] = current_time
        
        return False
    
    def _cleanup_rate_limits(self):
        """Clean up old rate limit entries."""
        current_time = time.time()
        cutoff_time = current_time - 300  # 5 minutes
        
        # Remove old entries
        old_keys = [
            key_id for key_id, info in self._rate_limit_cache.items()
            if info["last_cleanup"] < cutoff_time
        ]
        
        for key_id in old_keys:
            del self._rate_limit_cache[key_id]
    
    def _record_auth_success(self, api_key: APIKey, request_info: Dict = None):
        """Record successful authentication for analytics."""
        try:
            # Record usage analytics
            self.analytics.record_request(
                model_id="heidi-api-auth",
                request_tokens=0,
                response_tokens=0,
                response_time_ms=0,
                success=True,
                metadata={
                    "api_key_id": api_key.key_id,
                    "user_id": api_key.user_id,
                    "key_name": api_key.name,
                    "request_info": request_info or {}
                }
            )
        except Exception:
            # Don't fail authentication if analytics fails
            pass
    
    def check_permission(self, api_key: APIKey, permission: str) -> bool:
        """Check if the API key has a specific permission."""
        return permission in api_key.permissions
    
    def get_rate_limit_info(self, api_key: APIKey) -> Dict:
        """Get rate limit information for an API key."""
        key_id = api_key.key_id
        current_time = time.time()
        
        if key_id not in self._rate_limit_cache:
            return {
                "limit": api_key.rate_limit,
                "remaining": api_key.rate_limit,
                "reset_time": current_time + 60
            }
        
        rate_info = self._rate_limit_cache[key_id]
        
        # Count requests in the last minute
        cutoff_time = current_time - 60
        recent_requests = [
            req_time for req_time in rate_info["requests"]
            if req_time > cutoff_time
        ]
        
        return {
            "limit": api_key.rate_limit,
            "used": len(recent_requests),
            "remaining": max(0, api_key.rate_limit - len(recent_requests)),
            "reset_time": current_time + 60
        }


# Global instance
_authenticator = None


def get_authenticator() -> HeidiAuthenticator:
    """Get the global authenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = HeidiAuthenticator()
    return _authenticator
