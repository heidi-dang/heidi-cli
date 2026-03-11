from __future__ import annotations

import time
import logging
import threading
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from functools import lru_cache
from collections import OrderedDict

logger = logging.getLogger("heidi.performance")


@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int = 0
    ttl: float = 300.0


class LRUCache:
    def __init__(self, max_size: int = 100, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            entry = self.cache[key]
            if time.time() - entry.timestamp > entry.ttl:
                del self.cache[key]
                self.misses += 1
                return None

            entry.access_count += 1
            self.cache.move_to_end(key)
            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            self.cache[key] = CacheEntry(
                value=value, timestamp=time.time(), ttl=ttl or self.default_ttl
            )

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class PerformanceOptimizer:
    def __init__(self):
        self.response_cache = LRUCache(max_size=200, default_ttl=60.0)
        self.prompt_cache = LRUCache(max_size=500, default_ttl=300.0)
        self._lock = threading.Lock()
        self.request_times: Dict[str, list] = {}
        self.enabled = True

    def cache_key_from_messages(self, messages: list, model_id: str, **kwargs) -> str:
        import hashlib

        content = f"{model_id}:{messages}:{sorted(kwargs.items())}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        return self.response_cache.get(cache_key)

    def cache_response(self, cache_key: str, response: Dict[str, Any], ttl: float = 60.0):
        if not self.enabled:
            return
        self.response_cache.set(cache_key, response, ttl=ttl)

    def track_request_time(self, model_id: str, duration_ms: float):
        with self._lock:
            if model_id not in self.request_times:
                self.request_times[model_id] = []
            self.request_times[model_id].append(duration_ms)

            if len(self.request_times[model_id]) > 1000:
                self.request_times[model_id] = self.request_times[model_id][-1000:]

    def get_average_latency(self, model_id: str) -> float:
        with self._lock:
            times = self.request_times.get(model_id, [])
            return sum(times) / len(times) if times else 0.0

    def get_p50_latency(self, model_id: str) -> float:
        with self._lock:
            times = sorted(self.request_times.get(model_id, []))
            if not times:
                return 0.0
            idx = len(times) // 2
            return times[idx]

    def get_p95_latency(self, model_id: str) -> float:
        with self._lock:
            times = sorted(self.request_times.get(model_id, []))
            if not times:
                return 0.0
            idx = int(len(times) * 0.95)
            return times[idx]

    def get_p99_latency(self, model_id: str) -> float:
        with self._lock:
            times = sorted(self.request_times.get(model_id, []))
            if not times:
                return 0.0
            idx = int(len(times) * 0.99)
            return times[idx]

    def get_throughput(self, model_id: str, window_seconds: float = 60.0) -> float:
        with self._lock:
            times = self.request_times.get(model_id, [])
            if not times:
                return 0.0

            now = time.time()
            recent = [t for t in times if now - t <= window_seconds]
            return len(recent) / window_seconds

    def optimize_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        cache_key = f"prompt:{hash(prompt) % 10000}"
        cached = self.prompt_cache.get(cache_key)
        if cached:
            return cached

        optimized = self._apply_prompt_optimizations(prompt)
        self.prompt_cache.set(cache_key, optimized)
        return optimized

    def _apply_prompt_optimizations(self, prompt: str) -> str:
        prompt = prompt.strip()
        prompt = " ".join(prompt.split())
        return prompt

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache": {
                "response_hits": self.response_cache.hits,
                "response_misses": self.response_cache.misses,
                "response_hit_rate": self.response_cache.hit_rate,
                "prompt_hits": self.prompt_cache.hits,
                "prompt_misses": self.prompt_cache.misses,
                "prompt_hit_rate": self.prompt_cache.hit_rate,
            },
            "enabled": self.enabled,
        }


class AsyncBatchProcessor:
    def __init__(self, batch_size: int = 10, timeout: float = 1.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing = False

    async def add(self, item: Any) -> Any:
        future = asyncio.Future()
        await self.queue.put((item, future))
        return await asyncio.wait_for(future, timeout=self.timeout)

    async def process_batch(self, handler: Callable):
        self.processing = True
        batch = []
        futures = []

        while len(batch) < self.batch_size:
            try:
                item, future = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                batch.append(item)
                futures.append(future)
            except asyncio.TimeoutError:
                break

        if batch:
            results = await handler(batch)
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)

        self.processing = False


performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    return performance_optimizer
