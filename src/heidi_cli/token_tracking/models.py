"""
Token tracking database models and persistence layer.
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger("heidi.tokens")


@dataclass
class TokenUsage:
    """Token usage record."""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    model_id: str = ""
    session_id: str = ""
    user_id: str = "default"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_type: str = "chat_completion"  # chat_completion, embedding, etc.
    model_provider: str = "local"  # local, openai, anthropic, etc.
    cost_usd: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

    @property
    def cost_per_1k_tokens(self) -> float:
        """Calculate cost per 1k tokens."""
        if self.total_tokens == 0:
            return 0.0
        return (self.cost_usd / self.total_tokens) * 1000

    @property
    def timestamp_iso(self) -> str:
        """Get ISO format timestamp."""
        if self.timestamp:
            return self.timestamp.isoformat()
        return ""


@dataclass
class CostConfig:
    """Cost configuration for different models/providers."""
    provider: str
    model_id: str
    input_cost_per_1k: float  # USD per 1k input tokens
    output_cost_per_1k: float  # USD per 1k output tokens
    currency: str = "USD"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for given token usage."""
        input_cost = (prompt_tokens / 1000) * self.input_cost_per_1k
        output_cost = (completion_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost


class TokenDatabase:
    """Token usage database manager."""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("state/tokens.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    request_type TEXT NOT NULL,
                    model_provider TEXT NOT NULL,
                    cost_usd REAL NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    input_cost_per_1k REAL NOT NULL,
                    output_cost_per_1k REAL NOT NULL,
                    currency TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, model_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON token_usage(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_id ON token_usage(model_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON token_usage(session_id)
            """)
            
            conn.commit()
    
    def record_usage(self, usage: TokenUsage) -> int:
        """Record token usage to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO token_usage (
                    timestamp, model_id, session_id, user_id,
                    prompt_tokens, completion_tokens, total_tokens,
                    request_type, model_provider, cost_usd, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage.timestamp_iso,
                usage.model_id,
                usage.session_id,
                usage.user_id,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
                usage.request_type,
                usage.model_provider,
                usage.cost_usd,
                json.dumps(usage.metadata) if usage.metadata else None
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_usage_history(
        self,
        limit: int = 100,
        model_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TokenUsage]:
        """Get usage history with filters."""
        query = "SELECT * FROM token_usage WHERE 1=1"
        params = []
        
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                results.append(TokenUsage(
                    id=row['id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    model_id=row['model_id'],
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    prompt_tokens=row['prompt_tokens'],
                    completion_tokens=row['completion_tokens'],
                    total_tokens=row['total_tokens'],
                    request_type=row['request_type'],
                    model_provider=row['model_provider'],
                    cost_usd=row['cost_usd'],
                    metadata=metadata
                ))
            
            return results
    
    def get_usage_summary(
        self,
        period: str = "day",  # day, week, month, year
        model_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get usage summary for a period."""
        # Determine date range
        now = datetime.now(timezone.utc)
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Invalid period: {period}")
        
        query = """
            SELECT 
                COUNT(*) as total_requests,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                model_id
            FROM token_usage 
            WHERE timestamp >= ? AND timestamp <= ?
        """
        params = [start_date.isoformat(), now.isoformat()]
        
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " GROUP BY model_id"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            summary = {
                "period": period,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
                "by_model": {}
            }
            
            total_requests = 0
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0
            
            for row in cursor.fetchall():
                model_summary = {
                    "requests": row['total_requests'],
                    "prompt_tokens": row['total_prompt_tokens'] or 0,
                    "completion_tokens": row['total_completion_tokens'] or 0,
                    "total_tokens": row['total_tokens'] or 0,
                    "cost_usd": row['total_cost'] or 0.0
                }
                summary["by_model"][row['model_id']] = model_summary
                
                total_requests += row['total_requests']
                total_prompt_tokens += row['total_prompt_tokens'] or 0
                total_completion_tokens += row['total_completion_tokens'] or 0
                total_tokens += row['total_tokens'] or 0
                total_cost += row['total_cost'] or 0.0
            
            summary["total"] = {
                "requests": total_requests,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": total_cost
            }
            
            return summary
    
    def save_cost_config(self, config: CostConfig):
        """Save cost configuration."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cost_configs 
                (provider, model_id, input_cost_per_1k, output_cost_per_1k, currency, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config.provider,
                config.model_id,
                config.input_cost_per_1k,
                config.output_cost_per_1k,
                config.currency,
                now,
                now
            ))
            conn.commit()
    
    def get_cost_config(self, provider: str, model_id: str) -> Optional[CostConfig]:
        """Get cost configuration for a model."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM cost_configs 
                WHERE provider = ? AND model_id = ?
            """, (provider, model_id))
            
            row = cursor.fetchone()
            if row:
                return CostConfig(
                    provider=row['provider'],
                    model_id=row['model_id'],
                    input_cost_per_1k=row['input_cost_per_1k'],
                    output_cost_per_1k=row['output_cost_per_1k'],
                    currency=row['currency']
                )
            return None
    
    def export_usage(
        self,
        format: str = "json",  # json, csv
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Export usage data."""
        usage_history = self.get_usage_history(
            limit=10000,  # Large limit for export
            start_date=start_date,
            end_date=end_date
        )
        
        if format == "json":
            # Convert TokenUsage objects to dictionaries with ISO timestamps
            export_data = []
            for usage in usage_history:
                usage_dict = asdict(usage)
                usage_dict['timestamp'] = usage.timestamp_iso
                export_data.append(usage_dict)
            return json.dumps(export_data, indent=2)
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if usage_history:
                writer = csv.DictWriter(output, fieldnames=asdict(usage_history[0]).keys())
                writer.writeheader()
                for usage in usage_history:
                    writer.writerow(asdict(usage))
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global database instance
_db_instance: Optional[TokenDatabase] = None


def get_token_database() -> TokenDatabase:
    """Get global token database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TokenDatabase()
    return _db_instance
