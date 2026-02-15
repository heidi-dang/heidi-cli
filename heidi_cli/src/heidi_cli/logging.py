from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.logging import RichHandler

from .config import ConfigManager


console = Console()

SECRET_PATTERNS = [
    (re.compile(r"(ghp_[a-zA-Z0-9]{36})"), "***REDACTED***"),
    (re.compile(r"(gho_[a-zA-Z0-9]{36})"), "***REDACTED***"),
    (re.compile(r"(github_pat_[a-zA-Z0-9_]{22,})"), "***REDACTED***"),
    (re.compile(r"(COPILOT_GITHUB_TOKEN=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(COPILOT_TOKEN=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(GH_TOKEN=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(GITHUB_TOKEN=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(GITHUB_PAT=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(OPENAI_API_KEY=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r"(ANTHROPIC_API_KEY=)([^\s]*)"), r"\1***REDACTED***"),
    (re.compile(r'("token":\s*")[^"]+'), r"\1***REDACTED***"),
]


def redact_secrets(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class HeidiLogger:
    _run_id: Optional[str] = None
    _run_dir: Optional[Path] = None
    _logger: Optional[logging.Logger] = None

    @classmethod
    def init_run(cls, run_id: Optional[str] = None) -> str:
        cls._run_id = run_id or str(uuid.uuid4())[:8]
        cls._run_dir = ConfigManager.runs_dir() / cls._run_id
        cls._run_dir.mkdir(parents=True, exist_ok=True)

        cls._logger = logging.getLogger(f"heidi.{cls._run_id}")
        cls._logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(cls._run_dir / "stdout.log")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        cls._logger.addHandler(file_handler)

        return cls._run_id

    @classmethod
    def get_run_dir(cls) -> Optional[Path]:
        return cls._run_dir

    @classmethod
    def get_run_id(cls) -> Optional[str]:
        return cls._run_id

    @classmethod
    def debug(cls, msg: str) -> None:
        redacted = redact_secrets(msg)
        if cls._logger:
            cls._logger.debug(redacted)
        console.print(f"[dim]{redacted}[/dim]")

    @classmethod
    def info(cls, msg: str) -> None:
        redacted = redact_secrets(msg)
        if cls._logger:
            cls._logger.info(redacted)
        console.print(redacted)

    @classmethod
    def warning(cls, msg: str) -> None:
        redacted = redact_secrets(msg)
        if cls._logger:
            cls._logger.warning(redacted)
        console.print(f"[yellow]WARNING: {redacted}[/yellow]")

    @classmethod
    def error(cls, msg: str) -> None:
        redacted = redact_secrets(msg)
        if cls._logger:
            cls._logger.error(redacted)
        console.print(f"[red]ERROR: {redacted}[/red]")

    @classmethod
    def emit_status(cls, status: str) -> None:
        cls.info(f"[STATUS] {status}")
        cls.write_event("run_state", {"status": status, "phase": "status"})

    @classmethod
    def emit_message_delta(cls, content: str, chunk: str = "") -> None:
        """Emit a message delta for streaming text updates."""
        cls.write_event(
            "message_delta",
            {
                "content": content,
                "chunk": chunk,
            },
        )

    @classmethod
    def emit_tool_start(cls, tool_name: str, tool_input: dict = None) -> None:
        """Emit tool start event."""
        cls.write_event(
            "tool_start",
            {
                "tool": tool_name,
                "input": tool_input or {},
                "status": "started",
            },
        )

    @classmethod
    def emit_tool_log(cls, tool_name: str, log: str) -> None:
        """Emit tool log/output event."""
        cls.write_event(
            "tool_log",
            {
                "tool": tool_name,
                "log": log,
            },
        )

    @classmethod
    def emit_tool_done(cls, tool_name: str, tool_output: str = "") -> None:
        """Emit tool completion event."""
        cls.write_event(
            "tool_done",
            {
                "tool": tool_name,
                "output": tool_output,
                "status": "completed",
            },
        )

    @classmethod
    def emit_tool_error(cls, tool_name: str, error: str) -> None:
        """Emit tool error event."""
        cls.write_event(
            "tool_error",
            {
                "tool": tool_name,
                "error": error,
                "status": "failed",
            },
        )

    @classmethod
    def emit_run_state(cls, state: str, details: dict = None) -> None:
        """Emit run state change event."""
        cls.write_event(
            "run_state",
            {
                "state": state,
                "details": details or {},
            },
        )

    @classmethod
    def emit_thinking(cls, thinking: str) -> None:
        """Emit thinking state event for streaming UI."""
        cls.write_event("thinking", {"message": thinking})

    @classmethod
    def emit_log(cls, source: str, message: str) -> None:
        cls.info(f"[{source}] {message}")

    @classmethod
    def emit_result(cls, result: str) -> None:
        cls.info(f"[RESULT] {result}")

    @classmethod
    def write_event(cls, event_type: str, data: dict[str, Any]) -> None:
        if not cls._run_dir:
            return
        redacted_data = {k: redact_secrets(str(v)) for k, v in data.items()}
        transcript_file = cls._run_dir / "transcript.jsonl"
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": redacted_data,
        }
        with open(transcript_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    @classmethod
    def write_run_meta(cls, metadata: dict[str, Any]) -> None:
        if not cls._run_dir:
            return
        redacted_meta = {k: redact_secrets(str(v)) for k, v in metadata.items()}
        run_file = cls._run_dir / "run.json"

        # Merge with existing metadata instead of overwriting
        existing = {}
        if run_file.exists():
            try:
                existing = json.loads(run_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        merged = {**existing, **redacted_meta}
        run_file.write_text(json.dumps(merged, indent=2))


def setup_global_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
