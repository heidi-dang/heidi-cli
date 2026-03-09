from __future__ import annotations

import uuid
from typing import Optional
from .db import db

class RewardScorer:
    """Handles run scoring and strategy performance tracking."""

    async def record_reward(self, run_id: str, strategy_id: str, score: float, reason: Optional[str] = None):
        """Record a reward event and update strategy statistics."""
        event_id = str(uuid.uuid4())
        
        with db.get_connection() as conn:
            # 1. Record reward event
            conn.execute(
                "INSERT INTO reward_events (id, run_id, score, reason) VALUES (?, ?, ?, ?)",
                (event_id, run_id, score, reason)
            )
            
            # 2. Update strategy stats
            cursor = conn.execute("SELECT total_runs, avg_reward FROM strategy_stats WHERE strategy_id = ?", (strategy_id,))
            row = cursor.fetchone()
            
            if row:
                new_runs = row['total_runs'] + 1
                # Cumulative moving average
                new_avg = (row['avg_reward'] * row['total_runs'] + score) / new_runs
                conn.execute(
                    "UPDATE strategy_stats SET total_runs = ?, avg_reward = ?, last_used = CURRENT_TIMESTAMP WHERE strategy_id = ?",
                    (new_runs, new_avg, strategy_id)
                )
            else:
                conn.execute(
                    "INSERT INTO strategy_stats (strategy_id, total_runs, avg_reward, last_used) VALUES (?, 1, ?, CURRENT_TIMESTAMP)",
                    (strategy_id, score)
                )
            
            conn.commit()
            
        return event_id

reward_scorer = RewardScorer()
