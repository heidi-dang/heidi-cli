from __future__ import annotations

import random
from typing import List
from .db import db

class StrategySelector:
    """Selects the best model/strategy based on past performance."""

    def select_best_model(self, candidate_models: List[str], epsilon: float = 0.1) -> str:
        """
        Select a model using an epsilon-greedy approach.
        - Epsilon = Exploration rate (random choice)
        - 1-Epsilon = Exploitation (choose best performer)
        """
        if not candidate_models:
            raise ValueError("No candidate models provided for selection.")

        # 1. Exploration (Random)
        if random.random() < epsilon:
            return random.choice(candidate_models)

        # 2. Exploitation (Best Average Reward)
        with db.get_connection() as conn:
            placeholders = ",".join(["?"] * len(candidate_models))
            query = f"SELECT strategy_id, avg_reward FROM strategy_stats WHERE strategy_id IN ({placeholders}) ORDER BY avg_reward DESC"
            cursor = conn.execute(query, candidate_models)
            best_performer = cursor.fetchone()

        if best_performer:
            return best_performer['strategy_id']
        
        # Fallback to random if no stats yet
        return random.choice(candidate_models)

strategy_selector = StrategySelector()
