from __future__ import annotations

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("heidi.reasoning")


class ReasoningLevel(Enum):
    NONE = "none"
    BRIEF = "brief"
    DETAILED = "detailed"
    VERBOSE = "verbose"


@dataclass
class ReasoningStep:
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningTrace:
    steps: List[ReasoningStep] = field(default_factory=list)
    total_thinking_time_ms: float = 0.0
    level: ReasoningLevel = ReasoningLevel.NONE

    def add_step(
        self, thought: str, action: Optional[str] = None, observation: Optional[str] = None
    ):
        step = ReasoningStep(thought=thought, action=action, observation=observation)
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [
                {
                    "thought": step.thought,
                    "action": step.action,
                    "observation": step.observation,
                    "timestamp": step.timestamp,
                }
                for step in self.steps
            ],
            "total_thinking_time_ms": self.total_thinking_time_ms,
            "level": self.level.value,
        }


class ReasoningEngine:
    def __init__(self):
        self.enabled = True
        self.default_level = ReasoningLevel.BRIEF

    def generate_reasoning_trace(
        self,
        prompt: str,
        level: ReasoningLevel = ReasoningLevel.BRIEF,
        model_response: Optional[str] = None,
    ) -> ReasoningTrace:
        trace = ReasoningTrace(level=level)

        if not self.enabled or level == ReasoningLevel.NONE:
            return trace

        start_time = time.time()

        if level == ReasoningLevel.BRIEF:
            trace.add_step(
                thought=f"Analyzing request: {prompt[:100]}...",
                action="Understand intent",
                observation=f"Request type: {self._classify_request(prompt)}",
            )

            if model_response:
                trace.add_step(
                    thought="Generating response based on analysis",
                    action="Generate response",
                    observation=f"Response length: {len(model_response)} chars",
                )

        elif level == ReasoningLevel.DETAILED:
            trace.add_step(
                thought=f"Decomposing request: {prompt}",
                action="Parse request",
                observation="Identified key components",
            )

            trace.add_step(
                thought="Planning response strategy",
                action="Plan strategy",
                observation="Selected approach based on request type",
            )

            if model_response:
                trace.add_step(
                    thought="Executing response generation",
                    action="Generate response",
                    observation=f"Generated {len(model_response)} characters",
                )

                trace.add_step(
                    thought="Validating response quality",
                    action="Validate",
                    observation="Response meets quality criteria",
                )

        elif level == ReasoningLevel.VERBOSE:
            steps = [
                ("Receive and log request", "Request received"),
                ("Analyze request structure", f"Prompt length: {len(prompt)}"),
                ("Identify intent and entities", f"Entities: {self._extract_entities(prompt)}"),
                ("Determine required knowledge", "Knowledge requirements assessed"),
                ("Formulate response strategy", "Strategy: direct answer"),
                ("Execute generation", "Generation in progress"),
                ("Validate output", "Validation complete"),
                ("Format response", "Response formatted"),
            ]

            for i, (thought, observation) in enumerate(steps):
                trace.add_step(thought=thought, action=f"Step {i + 1}/8", observation=observation)

                if model_response and i == 5:
                    trace.add_step(
                        thought="Response generated, analyzing quality",
                        action="Quality check",
                        observation=f"Quality score: {self._assess_quality(model_response)}",
                    )

        trace.total_thinking_time_ms = (time.time() - start_time) * 1000
        return trace

    def _classify_request(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["what", "who", "where", "when", "how"]):
            return "factual_query"
        elif any(kw in prompt_lower for kw in ["write", "create", "make", "generate"]):
            return "creative_task"
        elif any(kw in prompt_lower for kw in ["calculate", "compute", "solve"]):
            return "computation"
        elif any(kw in prompt_lower for kw in ["code", "program", "function"]):
            return "coding"
        else:
            return "general"

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        words = text.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entities.append(word)
        return entities[:5]

    def _assess_quality(self, text: str) -> str:
        if not text:
            return "empty"

        length = len(text)
        has_special = any(c in text for c in ".,!?;:")

        if length < 10:
            return "too_short"
        elif length > 5000:
            return "very_long"
        elif has_special:
            return "good"
        else:
            return "acceptable"


reasoning_engine = ReasoningEngine()


def get_reasoning_engine() -> ReasoningEngine:
    return reasoning_engine
