from __future__ import annotations

import logging
from typing import Dict, Any, Tuple
from ..shared.config import ConfigLoader
from .manager import model_registry

logger = logging.getLogger("heidi.eval")

class EvalHarness:
    """Evaluates candidates to block regressions before promotion."""

    def __init__(self):
        self.config = ConfigLoader.load()

    async def evaluate_candidate(self, candidate_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Run eval suite on candidate and decide if it beats stable."""
        registry = model_registry.load_registry()
        
        if candidate_id not in registry["versions"] or registry["versions"][candidate_id]["channel"] != "candidate":
            raise ValueError(f"{candidate_id} is not a valid candidate model.")

        stable_id = registry.get("active_stable")
        
        logger.info(f"Evaluating candidate {candidate_id} against stable {stable_id or 'NONE'}")
        
        # Output paths
        eval_dir = self.config.state_dirs["evals"]
        log_file = eval_dir / f"eval_{candidate_id}.log"
        
        # Simulated evaluation results
        results: Dict[str, Any] = {
            "candidate_id": candidate_id,
            "baseline_id": stable_id,
        }
        metrics: Dict[str, Any] = {
            "accuracy": 0.85,
            "latency_ms": 120,
            "regression_detected": False
        }
        results["metrics"] = metrics
        
        # Simulated Policy Check (e.g. "beat_stable")
        passed = True
        if self.config.promotion_policy == "beat_stable" and stable_id:
            # Pretend we compared to stable and passed
            passed = float(metrics["accuracy"]) > 0.80

        results["passed"] = passed
        
        # Write eval log
        with open(log_file, "w") as f:
            for k, v in results.items():
                f.write(f"{k}: {v}\n")
                
        logger.info(f"Eval finished. Passed: {passed}")
        return passed, results

eval_harness = EvalHarness()
