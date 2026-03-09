from __future__ import annotations

import uuid
import json
from typing import Optional
from .db import db

class ReflectionEngine:
    """Synthesizes knowledge from past runs."""

    async def reflect_on_run(self, run_id: str, task: str, outcome: str, feedback: Optional[str] = None):
        """Analyze a single run and generate reflections/rules."""
        # Simple heuristic-based reflection for now
        # In a real implementation, this would call an LLM to "think" about the run
        
        conclusion = ""
        if outcome == "success":
            conclusion = f"Successfully completed task: {task}. The current strategy is effective."
        else:
            conclusion = f"Failed task: {task}. Need to investigate failure modes and adjust strategy."

        reflection_id = str(uuid.uuid4())
        
        with db.get_connection() as conn:
            # 1. Store reflection
            conn.execute(
                "INSERT INTO reflections (id, source_episode_ids, conclusion, confidence) VALUES (?, ?, ?, ?)",
                (reflection_id, json.dumps([run_id]), conclusion, 0.9 if outcome == "success" else 0.5)
            )
            
            # 2. Generate a procedural rule if it's a new successful pattern
            if outcome == "success":
                rule_text = f"When task is similar to '{task[:30]}...', proceed with current procedure."
                conn.execute(
                    "INSERT INTO rules (id, source_reflection_id, rule_text, rule_type) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), reflection_id, rule_text, 'procedure')
                )
            
            conn.commit()
            
        return reflection_id

reflection_engine = ReflectionEngine()
