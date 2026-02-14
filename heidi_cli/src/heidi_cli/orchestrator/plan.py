from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from .registry import AgentRegistry

BEGIN = "BEGIN_EXECUTION_HANDOFFS_YAML"
END = "END_EXECUTION_HANDOFFS_YAML"


@dataclass
class PlanResult:
    raw_text: str
    routing_yaml_text: str
    routing: dict[str, Any]


def extract_routing(text: str) -> str:
    m = re.search(rf"{BEGIN}\s*(.*?)\s*{END}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"Missing routing block markers: {BEGIN} ... {END}")
    return m.group(1).strip()


def parse_routing(yaml_text: str) -> dict[str, Any]:
    data = yaml.safe_load(yaml_text) or {}
    if "execution_handoffs" not in data or not isinstance(data["execution_handoffs"], list):
        raise ValueError("routing YAML must contain execution_handoffs: [ ... ]")
    return data


def build_plan_prompt(task: str) -> str:
    agent = AgentRegistry.get("Plan")
    if not agent:
        raise ValueError("Plan agent not found in registry")
    return f"""{agent["prompt"]}

TASK:
{task}
"""
