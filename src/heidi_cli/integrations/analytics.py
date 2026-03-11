from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger("heidi.analytics")


@dataclass
class ModelUsage:
    """Model usage statistics."""

    model_id: str
    request_count: int
    total_tokens: int
    total_response_time: float
    avg_response_time: float
    success_rate: float
    error_count: int
    last_used: datetime
    created_at: datetime


@dataclass
class ModelPerformance:
    """Model performance metrics."""

    model_id: str
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_requests_per_min: float
    error_rate: float
    token_efficiency: float
    last_updated: datetime


class UsageAnalytics:
    """Track and analyze model usage patterns."""

    def __init__(self, data_root: Optional[Path] = None):
        if data_root is None:
            data_root = Path.home() / ".heidi"

        self.data_root = data_root
        self.db_path = self.data_root / "analytics" / "usage.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the analytics database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    request_tokens INTEGER,
                    response_tokens INTEGER,
                    response_time_ms REAL,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    model_id TEXT PRIMARY KEY,
                    request_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_response_time REAL DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    success_rate REAL DEFAULT 1.0,
                    error_count INTEGER DEFAULT 0,
                    last_used DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_usage_model_id 
                ON model_usage(model_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_usage_timestamp 
                ON model_usage(timestamp)
            """)

    def record_request(
        self,
        model_id: str,
        request_tokens: int,
        response_tokens: int,
        response_time_ms: float,
        success: bool = True,
        error_message: str = None,
    ):
        """Record a model request."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Record individual request
                    conn.execute(
                        """
                        INSERT INTO model_usage 
                        (model_id, request_tokens, response_tokens, response_time_ms, success, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            model_id,
                            request_tokens,
                            response_tokens,
                            response_time_ms,
                            success,
                            error_message,
                        ),
                    )

                    # Update performance summary
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO model_performance 
                        (model_id, request_count, total_tokens, total_response_time, 
                         avg_response_time, success_rate, error_count, last_used, updated_at)
                        VALUES (
                            ?,
                            COALESCE((SELECT request_count FROM model_performance WHERE model_id = ?), 0) + 1,
                            COALESCE((SELECT total_tokens FROM model_performance WHERE model_id = ?), 0) + ?,
                            COALESCE((SELECT total_response_time FROM model_performance WHERE model_id = ?), 0) + ?,
                            COALESCE((SELECT avg_response_time FROM model_performance WHERE model_id = ?), 0) * 0.9 + ? * 0.1,
                            COALESCE((SELECT success_rate FROM model_performance WHERE model_id = ?), 1.0) * 0.95 + ? * 0.05,
                            COALESCE((SELECT error_count FROM model_performance WHERE model_id = ?), 0) + ?,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """,
                        (
                            model_id,
                            model_id,
                            model_id,
                            request_tokens + response_tokens,
                            model_id,
                            response_time_ms,
                            model_id,
                            response_time_ms,
                            model_id,
                            float(success),
                            model_id,
                            int(not success),
                        ),
                    )

            except Exception as e:
                logger.error(f"Failed to record usage: {e}")

    def get_model_usage(self, model_id: str, days: int = 30) -> Optional[ModelUsage]:
        """Get usage statistics for a specific model."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT 
                    request_count,
                    total_tokens,
                    avg_response_time,
                    success_rate,
                    error_count,
                    last_used,
                    created_at
                FROM model_performance 
                WHERE model_id = ?
            """,
                (model_id,),
            )

            row = cursor.fetchone()
            if row:
                return ModelUsage(
                    model_id=model_id,
                    request_count=row[0],
                    total_tokens=row[1],
                    total_response_time=row[2] * row[0],  # Convert avg back to total
                    avg_response_time=row[2],
                    success_rate=row[3],
                    error_count=row[4],
                    last_used=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                )
        return None

    def get_top_models(self, limit: int = 10, days: int = 30) -> List[ModelUsage]:
        """Get top models by usage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT 
                    model_id,
                    request_count,
                    total_tokens,
                    avg_response_time,
                    success_rate,
                    error_count,
                    last_used,
                    created_at
                FROM model_performance 
                WHERE last_used >= datetime('now', '-' || ? || ' days')
                ORDER BY request_count DESC
                LIMIT ?
            """,
                (days, limit),
            )

            models = []
            for row in cursor.fetchall():
                models.append(
                    ModelUsage(
                        model_id=row[0],
                        request_count=row[1],
                        total_tokens=row[2],
                        total_response_time=row[3] * row[1],
                        avg_response_time=row[3],
                        success_rate=row[4],
                        error_count=row[5],
                        last_used=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                        created_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    )
                )

            return models

    def get_performance_metrics(self, model_id: str, days: int = 7) -> Optional[ModelPerformance]:
        """Get detailed performance metrics for a model."""
        with sqlite3.connect(self.db_path) as conn:
            # Get latency percentiles
            cursor = conn.execute(
                """
                SELECT 
                    response_time_ms
                FROM model_usage 
                WHERE model_id = ? 
                AND timestamp >= datetime('now', '-{} days')
                AND success = TRUE
                ORDER BY response_time_ms
            """.format(days),
                (model_id,),
            )

            latencies = [row[0] for row in cursor.fetchall()]

            if not latencies:
                return None

            # Calculate percentiles
            latencies.sort()
            p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 20 else latencies[-1]
            p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) > 100 else latencies[-1]
            avg_latency = sum(latencies) / len(latencies)

            # Get throughput (requests per minute)
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H:%M', timestamp)) as unique_minutes
                FROM model_usage 
                WHERE model_id = ? 
                AND timestamp >= datetime('now', '-{} days')
            """.format(days),
                (model_id,),
            )

            unique_minutes = cursor.fetchone()[0] or 1
            total_requests = len(latencies)
            throughput = total_requests / max(unique_minutes, 1)

            # Get error rate
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as errors
                FROM model_usage 
                WHERE model_id = ? 
                AND timestamp >= datetime('now', '-{} days')
            """.format(days),
                (model_id,),
            )

            total, errors = cursor.fetchone()
            error_rate = errors / total if total > 0 else 0

            # Calculate token efficiency (tokens per second)
            cursor = conn.execute(
                """
                SELECT AVG(request_tokens + response_tokens) as avg_tokens
                FROM model_usage 
                WHERE model_id = ? 
                AND success = TRUE
                AND timestamp >= datetime('now', '-{} days')
            """.format(days),
                (model_id,),
            )

            avg_tokens = cursor.fetchone()[0] or 0
            token_efficiency = avg_tokens / (avg_latency / 1000) if avg_latency > 0 else 0

            return ModelPerformance(
                model_id=model_id,
                avg_latency_ms=avg_latency,
                p95_latency_ms=p95,
                p99_latency_ms=p99,
                throughput_requests_per_min=throughput,
                error_rate=error_rate,
                token_efficiency=token_efficiency,
                last_updated=datetime.now(),
            )

    def get_usage_trends(self, model_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get usage trends over time."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as requests,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(request_tokens + response_tokens) as total_tokens,
                    SUM(CASE WHEN success = FALSE THEN 1 ELSE 0 END) as errors
                FROM model_usage 
                WHERE model_id = ? 
                AND timestamp >= datetime('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            """.format(days),
                (model_id,),
            )

            trends = []
            for row in cursor.fetchall():
                trends.append(
                    {
                        "date": row[0],
                        "requests": row[1],
                        "avg_response_time": row[2],
                        "total_tokens": row[3],
                        "errors": row[4],
                        "success_rate": (row[1] - row[4]) / row[1] if row[1] > 0 else 1.0,
                    }
                )

            return trends

    def export_analytics(self, model_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Export analytics data for analysis."""
        data = {"exported_at": datetime.now().isoformat(), "period_days": days, "models": {}}

        if model_id:
            # Export specific model
            usage = self.get_model_usage(model_id, days)
            performance = self.get_performance_metrics(model_id, days)
            trends = self.get_usage_trends(model_id, days)

            if usage:
                data["models"][model_id] = {
                    "usage": asdict(usage),
                    "performance": asdict(performance) if performance else None,
                    "trends": trends,
                }
        else:
            # Export all models
            for model_usage in self.get_top_models(limit=50, days=days):
                model_id = model_usage.model_id
                performance = self.get_performance_metrics(model_id, days)
                trends = self.get_usage_trends(model_id, days)

                data["models"][model_id] = {
                    "usage": asdict(model_usage),
                    "performance": asdict(performance) if performance else None,
                    "trends": trends,
                }

        return data


# Global analytics instance
_analytics_instance = None


def get_analytics() -> UsageAnalytics:
    """Get the global analytics instance."""
    global _analytics_instance
    if _analytics_instance is None:
        import os

        data_root = os.environ.get("HEIDI_ANALYTICS_PATH")
        if data_root:
            _analytics_instance = UsageAnalytics(data_root=Path(data_root))
        else:
            _analytics_instance = UsageAnalytics()
    return _analytics_instance
