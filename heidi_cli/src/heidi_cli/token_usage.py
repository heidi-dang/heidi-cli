from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .config import ConfigManager


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model: str = "gpt-5"
    provider: str = "copilot"

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.estimated_cost,
            "model": self.model,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenUsage":
        return cls(**data)


PRICING = {
    "gpt-5": {"prompt": 0.005, "completion": 0.015},  # per 1K tokens
    "gpt-4o": {"prompt": 0.0025, "completion": 0.01},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
    "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    "ollama": {"prompt": 0.0, "completion": 0.0},
    "lmstudio": {"prompt": 0.0, "completion": 0.0},
}


def calculate_cost(
    prompt_tokens: int, completion_tokens: int, model: str, provider: str = "copilot"
) -> float:
    if provider in ("ollama", "lmstudio"):
        return 0.0

    pricing = PRICING.get(model, PRICING["gpt-5"])
    prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * pricing["completion"]
    return prompt_cost + completion_cost


def record_usage(run_id: str, usage: TokenUsage) -> None:
    runs_dir = ConfigManager.runs_dir()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    usage_file = run_dir / "usage.json"
    usage_file.write_text(json.dumps(usage.to_dict(), indent=2))


def get_usage(run_id: str) -> Optional[TokenUsage]:
    runs_dir = ConfigManager.runs_dir()
    usage_file = runs_dir / run_id / "usage.json"

    if not usage_file.exists():
        return None

    data = json.loads(usage_file.read_text())
    return TokenUsage.from_dict(data)


def get_total_usage() -> dict:
    runs_dir = ConfigManager.runs_dir()
    if not runs_dir.exists():
        return {"total_tokens": 0, "total_cost": 0.0, "runs": 0}

    total_tokens = 0
    total_cost = 0.0
    runs = 0

    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        usage_file = run_dir / "usage.json"
        if usage_file.exists():
            data = json.loads(usage_file.read_text())
            total_tokens += data.get("total_tokens", 0)
            total_cost += data.get("estimated_cost", 0.0)
            runs += 1

    return {
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "runs": runs,
    }
