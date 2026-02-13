from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from copilot import CopilotClient


class CopilotRuntime:
    """Thin wrapper around CopilotClient with sensible defaults."""

    def __init__(
        self,
        model: Optional[str] = None,
        github_token: Optional[str] = None,
        log_level: str = "error",
        cwd: Optional[Path] = None,
    ):
        self.model = model or os.getenv("COPILOT_MODEL", "gpt-5")
        
        # Try env vars first, then fall back to ConfigManager
        self.github_token = (
            github_token
            or os.getenv("COPILOT_GITHUB_TOKEN")
            or os.getenv("GH_TOKEN")
            or os.getenv("GITHUB_TOKEN")
        )
        
        if not self.github_token:
            try:
                from .config import ConfigManager
                self.github_token = ConfigManager.get_github_token()
            except Exception:
                pass
        
        self.cwd = cwd or Path.cwd()
        
        client_config = {
            "log_level": log_level,
        }
        
        if self.github_token:
            client_config["github_token"] = self.github_token
            client_config["use_logged_in_user"] = False
        else:
            client_config["use_logged_in_user"] = True
        
        # Add workspace/cwd if supported by SDK
        client_config["cwd"] = str(self.cwd)
        
        self.client = CopilotClient(client_config)
        self._session = None

    async def start(self) -> None:
        await self.client.start()
        self._session = await self.client.create_session({"model": self.model})

    async def stop(self) -> None:
        try:
            if self._session is not None:
                await self._session.destroy()
        finally:
            await self.client.stop()

    async def send_and_wait(self, prompt: str, timeout_s: int = 120) -> str:
        if self._session is None:
            raise RuntimeError("CopilotRuntime not started")
        done = asyncio.Event()
        chunks: list[str] = []

        def on_event(event):
            # Copilot SDK emits typed events; we match by string to stay forward-compatible
            t = getattr(getattr(event, "type", None), "value", None) or getattr(event, "type", None)
            if t == "assistant.message":
                content = getattr(getattr(event, "data", None), "content", None)
                if isinstance(content, str):
                    chunks.append(content)
            elif t == "session.idle":
                done.set()

        self._session.on(on_event)
        await self._session.send({"prompt": prompt})
        await asyncio.wait_for(done.wait(), timeout=timeout_s)
        return "".join(chunks).strip()
