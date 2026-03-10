from __future__ import annotations

import logging
import json
import asyncio
import time
from typing import Dict, Any, Tuple, List
from pathlib import Path
from ..shared.config import ConfigLoader
from .manager import model_registry
from ..model_host.manager import manager as model_manager

logger = logging.getLogger("heidi.eval")

class EvalHarness:
    """Evaluates candidates to block regressions before promotion."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.eval_tasks = [
            {
                "name": "code_generation",
                "prompt": "Write a Python function to calculate fibonacci numbers.",
                "expected_keywords": ["def", "fibonacci", "return"],
                "weight": 0.3
            },
            {
                "name": "reasoning", 
                "prompt": "Explain the difference between recursion and iteration.",
                "expected_keywords": ["recursion", "iteration", "function", "loop"],
                "weight": 0.2
            },
            {
                "name": "debugging",
                "prompt": "Debug this Python code: for i in range(10): print(i)",
                "expected_keywords": ["code", "print", "range"],
                "weight": 0.2
            },
            {
                "name": "creativity",
                "prompt": "Write a short poem about programming.",
                "expected_keywords": ["code", "program", "lines"],
                "weight": 0.15
            },
            {
                "name": "speed",
                "prompt": "What is 2+2?",
                "expected_keywords": ["4", "four"],
                "weight": 0.15
            }
        ]

    async def evaluate_candidate(self, candidate_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Run eval suite on candidate and decide if it beats stable."""
        registry = model_registry.load_registry()
        
        if candidate_id not in registry["versions"] or registry["versions"][candidate_id]["channel"] != "candidate":
            raise ValueError(f"{candidate_id} is not a valid candidate model.")

        stable_id = registry.get("active_stable")
        
        logger.info(f"Evaluating candidate {candidate_id} against stable {stable_id or 'NONE'}")
        
        # Output paths
        eval_dir = self.config.state_dirs["evals"]
        eval_dir.mkdir(parents=True, exist_ok=True)
        log_file = eval_dir / f"eval_{candidate_id}.log"
        
        # Run evaluation tasks
        candidate_results = await self._run_model_evaluation(candidate_id)
        stable_results = {}
        
        if stable_id:
            stable_results = await self._run_model_evaluation(stable_id)
        
        # Compare results
        comparison = self._compare_results(candidate_results, stable_results)
        
        # Make decision based on policy
        passed = self._apply_promotion_policy(comparison, candidate_id, stable_id)
        
        results = {
            "candidate_id": candidate_id,
            "baseline_id": stable_id,
            "eval_tasks": len(self.eval_tasks),
            "candidate_metrics": candidate_results,
            "stable_metrics": stable_results,
            "comparison": comparison,
            "passed": passed,
            "evaluated_at": time.time()
        }
        
        # Write eval log
        with open(log_file, "w") as f:
            json.dump(results, f, indent=2)
                
        logger.info(f"Eval finished. Passed: {passed}")
        return passed, results
    
    async def _run_model_evaluation(self, model_id: str) -> Dict[str, Any]:
        """Run evaluation tasks on a specific model."""
        results = {
            "total_tasks": len(self.eval_tasks),
            "passed_tasks": 0,
            "total_response_time": 0.0,
            "task_results": []
        }
        
        for task in self.eval_tasks:
            start_time = time.time()
            
            try:
                messages = [{"role": "user", "content": task["prompt"]}]
                response = await model_manager.get_response(
                    model_id=model_id,
                    messages=messages,
                    max_tokens=200,
                    temperature=0.1
                )
                
                response_time = time.time() - start_time
                content = response["choices"][0]["message"]["content"]
                
                # Check if expected keywords are present
                keywords_found = sum(1 for keyword in task["expected_keywords"] 
                                    if keyword.lower() in content.lower())
                
                task_passed = keywords_found >= len(task["expected_keywords"]) * 0.5  # 50% keywords threshold
                
                task_result = {
                    "task_name": task["name"],
                    "passed": task_passed,
                    "keywords_found": keywords_found,
                    "keywords_expected": len(task["expected_keywords"]),
                    "response_time": response_time,
                    "response_length": len(content),
                    "content_preview": content[:100] + "..." if len(content) > 100 else content
                }
                
                results["task_results"].append(task_result)
                results["total_response_time"] += response_time
                
                if task_passed:
                    results["passed_tasks"] += 1
                    
            except Exception as e:
                logger.error(f"Error evaluating task {task['name']} for model {model_id}: {e}")
                results["task_results"].append({
                    "task_name": task["name"],
                    "passed": False,
                    "error": str(e)
                })
        
        # Calculate aggregate metrics
        results["accuracy"] = results["passed_tasks"] / results["total_tasks"]
        results["avg_response_time"] = results["total_response_time"] / results["total_tasks"]
        
        return results
    
    def _compare_results(self, candidate: Dict[str, Any], stable: Dict[str, Any]) -> Dict[str, Any]:
        """Compare candidate results against stable baseline."""
        comparison = {
            "accuracy_improvement": 0.0,
            "speed_improvement": 0.0,
            "regression_detected": False
        }
        
        if stable:
            comparison["accuracy_improvement"] = candidate["accuracy"] - stable["accuracy"]
            comparison["speed_improvement"] = stable["avg_response_time"] - candidate["avg_response_time"]
            comparison["regression_detected"] = comparison["accuracy_improvement"] < -0.1  # 10% regression threshold
        
        return comparison
    
    def _apply_promotion_policy(self, comparison: Dict[str, Any], candidate_id: str, stable_id: Optional[str]) -> bool:
        """Apply promotion policy to determine if candidate should be promoted."""
        policy = self.config.promotion_policy
        
        if policy == "beat_stable":
            if not stable_id:
                # No stable model, promote if accuracy > 0.7
                return comparison["candidate_metrics"]["accuracy"] > 0.7
            else:
                # Must beat stable on accuracy and no significant regression
                return (
                    comparison["accuracy_improvement"] > 0.05 and  # 5% improvement
                    not comparison["regression_detected"]
                )
        
        elif policy == "conservative":
            # Require higher accuracy and no regression
            return (
                comparison["candidate_metrics"]["accuracy"] > 0.8 and
                not comparison["regression_detected"] and
                comparison["accuracy_improvement"] > 0.1  # 10% improvement
            )
        
        elif policy == "aggressive":
            # Any improvement or no major regression
            return not comparison["regression_detected"]
        
        else:
            # Default to conservative
            return self._apply_promotion_policy(comparison, candidate_id, stable_id, "conservative")

eval_harness = EvalHarness()
