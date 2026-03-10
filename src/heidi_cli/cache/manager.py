"""
Enhanced caching system with Redis support and intelligent cache management.
"""

from __future__ import annotations

import json
import hashlib
import pickle
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod
import threading

logger = logging.getLogger("heidi.cache")

class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    FIFO = "fifo"

class CacheLevel(Enum):
    """Cache levels for hierarchy."""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[int] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()
    
    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1

@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    eviction_count: int = 0
    hits: int = 0
    misses: int = 0
    
    @property
    def total_requests(self) -> int:
        """Total number of requests."""
        return self.hits + self.misses
    
    def update_hit(self):
        """Update hit statistics."""
        self.hits += 1
        self._update_rates()
    
    def update_miss(self):
        """Update miss statistics."""
        self.misses += 1
        self._update_rates()
    
    def update_eviction(self):
        """Update eviction count."""
        self.eviction_count += 1
    
    def _update_rates(self):
        """Update hit/miss rates."""
        if self.total_requests > 0:
            self.hit_rate = (self.hits / self.total_requests) * 100
            self.miss_rate = (self.misses / self.total_requests) * 100

class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass

class MemoryCache(CacheBackend):
    """In-memory cache with LRU eviction."""
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 10000,
                 strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.strategy = strategy
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU
        self._lock = threading.RLock()
        self._stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats.update_miss()
                return None
            
            if entry.is_expired:
                self._remove_entry(key)
                self._stats.update_miss()
                return None
            
            entry.touch()
            
            # Update access order for LRU
            if self.strategy == CacheStrategy.LRU:
                self._update_access_order(key)
            
            self._stats.update_hit()
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        try:
            # Calculate size
            size_bytes = len(pickle.dumps(value))
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds
            )
            
            with self._lock:
                # Check if we need to evict
                self._ensure_capacity(size_bytes)
                
                # Remove existing entry if present
                if key in self._cache:
                    self._remove_entry(key)
                
                # Add new entry
                self._cache[key] = entry
                self._access_order.append(key)
                self._update_stats()
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache entry: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()
            return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            entry = self._cache.get(key)
            return entry is not None and not entry.is_expired
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        with self._lock:
            import fnmatch
            return [key for key in self._cache.keys() 
                   if fnmatch.fnmatch(key, pattern)]
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return self._stats
    
    def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry."""
        while (len(self._cache) >= self.max_entries or 
               self._get_total_size() + new_entry_size > self.max_size_bytes):
            
            if not self._cache:
                break
            
            # Evict based on strategy
            if self.strategy == CacheStrategy.LRU:
                self._evict_lru()
            elif self.strategy == CacheStrategy.LFU:
                self._evict_lfu()
            elif self.strategy == CacheStrategy.FIFO:
                self._evict_fifo()
            elif self.strategy == CacheStrategy.TTL:
                self._evict_expired()
            
            self._stats.update_eviction()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._access_order:
            lru_key = self._access_order[0]
            self._remove_entry(lru_key)
    
    def _evict_lfu(self):
        """Evict least frequently used entry."""
        if not self._cache:
            return
        
        lfu_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].access_count)
        self._remove_entry(lfu_key)
    
    def _evict_fifo(self):
        """Evict oldest entry (FIFO)."""
        if self._cache:
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k].created_at)
            self._remove_entry(oldest_key)
    
    def _evict_expired(self):
        """Evict expired entries."""
        expired_keys = [key for key, entry in self._cache.items()
                       if entry.is_expired]
        for key in expired_keys:
            self._remove_entry(key)
    
    def _remove_entry(self, key: str):
        """Remove entry from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _update_access_order(self, key: str):
        """Update access order for LRU."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _get_total_size(self) -> int:
        """Get total cache size in bytes."""
        return sum(entry.size_bytes for entry in self._cache.values())
    
    def _update_stats(self):
        """Update cache statistics."""
        self._stats.total_entries = len(self._cache)
        self._stats.total_size_bytes = self._get_total_size()

class RedisCache(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 prefix: str = "heidi:"):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self._client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False  # Handle binary data
            )
            # Test connection
            self._client.ping()
            logger.info("Connected to Redis cache")
        except ImportError:
            logger.warning("Redis not available, using fallback cache")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        if not self._client:
            return None
        
        try:
            prefixed_key = f"{self.prefix}{key}"
            data = self._client.get(prefixed_key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        if not self._client:
            return False
        
        try:
            prefixed_key = f"{self.prefix}{key}"
            data = pickle.dumps(value)
            
            if ttl_seconds:
                return self._client.setex(prefixed_key, ttl_seconds, data)
            else:
                return self._client.set(prefixed_key, data)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key."""
        if not self._client:
            return False
        
        try:
            prefixed_key = f"{self.prefix}{key}"
            return bool(self._client.delete(prefixed_key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache with prefix."""
        if not self._client:
            return False
        
        try:
            pattern = f"{self.prefix}*"
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys) > 0
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            return False
        
        try:
            prefixed_key = f"{self.prefix}{key}"
            return bool(self._client.exists(prefixed_key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if not self._client:
            return []
        
        try:
            prefixed_pattern = f"{self.prefix}{pattern}"
            redis_keys = self._client.keys(prefixed_pattern)
            # Remove prefix from returned keys
            return [key.decode('utf-8')[len(self.prefix):] 
                   for key in redis_keys if key.decode('utf-8').startswith(self.prefix)]
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

class CacheManager:
    """Multi-level cache manager with intelligent routing."""
    
    def __init__(self, memory_size_mb: int = 100, redis_host: str = "localhost",
                 redis_port: int = 6379, enable_redis: bool = True):
        
        # Initialize cache levels
        self.memory_cache = MemoryCache(max_size_mb=memory_size_mb)
        self.redis_cache = None
        
        if enable_redis:
            self.redis_cache = RedisCache(host=redis_host, port=redis_port)
        
        self._lock = threading.RLock()
    
    def get(self, key: str, level: CacheLevel = CacheLevel.MEMORY) -> Optional[Any]:
        """Get value from cache, trying levels in order."""
        # Try memory first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try Redis if available
        if self.redis_cache and level != CacheLevel.MEMORY:
            value = self.redis_cache.get(key)
            if value is not None:
                # Promote to memory cache
                self.memory_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
            level: CacheLevel = CacheLevel.MEMORY) -> bool:
        """Set value in specified cache level(s)."""
        success = True
        
        if level in [CacheLevel.MEMORY, CacheLevel.REDIS]:
            success &= self.memory_cache.set(key, value, ttl_seconds)
        
        if self.redis_cache and level in [CacheLevel.REDIS, CacheLevel.DISK]:
            success &= self.redis_cache.set(key, value, ttl_seconds)
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete from all cache levels."""
        success = True
        success &= self.memory_cache.delete(key)
        
        if self.redis_cache:
            success &= self.redis_cache.delete(key)
        
        return success
    
    def clear(self, level: CacheLevel = CacheLevel.MEMORY) -> bool:
        """Clear specified cache level."""
        if level == CacheLevel.MEMORY:
            return self.memory_cache.clear()
        elif level == CacheLevel.REDIS and self.redis_cache:
            return self.redis_cache.clear()
        elif level == CacheLevel.DISK:
            # Clear all levels
            success = self.memory_cache.clear()
            if self.redis_cache:
                success &= self.redis_cache.clear()
            return success
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all cache levels."""
        stats = {
            "memory": asdict(self.memory_cache.get_stats()),
            "redis": {"available": self.redis_cache is not None}
        }
        
        if self.redis_cache:
            # Could add Redis stats here if needed
            pass
        
        return stats
    
    def cache_response(self, model_id: str, messages: List[Dict[str, str]],
                      response: Dict[str, Any], ttl_seconds: int = 3600) -> str:
        """Cache a model response."""
        # Create cache key from model and messages
        key_data = {
            "model_id": model_id,
            "messages": messages
        }
        cache_key = f"response:{hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()}"
        
        self.set(cache_key, response, ttl_seconds)
        return cache_key
    
    def get_cached_response(self, model_id: str, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Get cached model response."""
        key_data = {
            "model_id": model_id,
            "messages": messages
        }
        cache_key = f"response:{hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()}"
        
        return self.get(cache_key)
    
    def invalidate_model_cache(self, model_id: str):
        """Invalidate all cache entries for a model."""
        pattern = f"response:*"
        keys = self.memory_cache.keys(pattern)
        
        # This is a simplified approach - in production, you'd want
        # more sophisticated cache invalidation
        for key in keys:
            self.delete(key)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
