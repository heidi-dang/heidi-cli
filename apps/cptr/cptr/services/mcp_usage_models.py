"""Strict payload-only models for ChatGPT MCP usage telemetry."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class McpUsageDiagnostic(BaseModel):
    """One bounded MCP-visible usage event received from the Heidi MCP adapter."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["usage"] = "usage"
    version: Literal[1] = 1
    event_id: str = Field(min_length=1, max_length=128)
    timestamp_ms: int = Field(ge=0)
    request_id: str | None = Field(default=None, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    client_id: str = Field(default="chatgpt", min_length=1, max_length=128)
    model_reported: str | None = Field(default=None, max_length=120)
    model_canonical: str | None = Field(default=None, max_length=64)
    model_source: Literal["self_reported", "unavailable"]
    tool_name: str = Field(min_length=1, max_length=256)
    input_tokens_estimated: int = Field(ge=0, le=100_000_000)
    output_tokens_estimated: int = Field(ge=0, le=100_000_000)
    cached_input_tokens_estimated: None = None
    estimator_method: str = Field(min_length=1, max_length=160)
    estimator_exact_for_model: bool = False
    status: Literal["complete", "error"]
