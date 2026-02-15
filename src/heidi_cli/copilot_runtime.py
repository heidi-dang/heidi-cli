from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from copilot import CopilotClient


async def list_copilot_models() -> list[dict]:
    """List available Copilot models."""
    models = []
    try:
        client = CopilotClient({"use_logged_in_user": True})
        await client.start()
        try:
            raw_models = await client.list_models()
            for m in raw_models if isinstance(raw_models, list) else []:
                mid = m.get("id") if isinstance(m, dict) else getattr(m, "id", "")
                if not mid:
                    continue
                billing = m.get("billing", {}) if isinstance(m, dict) else getattr(m, "billing", {})
                multiplier = (
                    float(billing.get("multiplier", 1)) if isinstance(billing, dict) else 1.0
                )
                models.append(
                    {
                        "id": mid,
                        "name": mid,
                        "multiplier": multiplier,
                    }
                )
        finally:
            await client.stop()
    except Exception as e:
        return [{"error": str(e)}]
    return models


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

        # Token precedence (highest to lowest):
        # 1. Explicit parameter passed to constructor
        # 2. GH_TOKEN env var (GitHub CLI token)
        # 3. GITHUB_TOKEN env var (GitHub Actions / general use)
        # 4. Token stored via ConfigManager (keyring or secrets file)
        # Note: If multiple env vars are set, GH_TOKEN takes precedence and a warning is logged.
        gh_token_env = os.getenv("GH_TOKEN")
        github_token_env = os.getenv("GITHUB_TOKEN")

        if gh_token_env and github_token_env:
            import sys

            print(
                "[yellow]Warning: Both GH_TOKEN and GITHUB_TOKEN are set.[/yellow]",
                "[yellow]Using GH_TOKEN (GH_TOKEN takes precedence).[/yellow]",
                file=sys.stderr,
            )

        # Use parameter if provided, otherwise fall back to env vars
        if github_token:
            self.github_token = github_token
            self._token_source = "constructor argument"
        elif gh_token_env:
            self.github_token = gh_token_env
            self._token_source = "GH_TOKEN"
            import sys

            print(
                "[yellow]Warning: Using token from GH_TOKEN env var.[/yellow]",
                "[yellow]This overrides stored OAuth token. Copilot may fail if env var token lacks Copilot scope.[/yellow]",
                file=sys.stderr,
            )
        elif github_token_env:
            self.github_token = github_token_env
            self._token_source = "GITHUB_TOKEN"
            import sys

            print(
                "[yellow]Warning: Using token from GITHUB_TOKEN env var.[/yellow]",
                "[yellow]This overrides stored OAuth token. Copilot may fail if env var token lacks Copilot scope.[/yellow]",
                file=sys.stderr,
            )
        else:
            self.github_token = None
            self._token_source = None

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
