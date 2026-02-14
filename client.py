"""
title: Heidi CLI Pipe
description: Control Copilot/Jules/OpenCode agents from OpenWebUI via Heidi CLI
author: Heidi
version: 2.1.0
"""

import traceback
from typing import List, Union, Generator, Iterator

import requests
from pydantic import BaseModel, Field


COPILOT_MODELS = [
    "gpt-5",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "gpt-4o",
    "gpt-4o-mini",
    "o3",
    "o4-mini",
]


class Pipe:
    class Valves(BaseModel):
        HEIDI_SERVER_URL: str = Field(
            default="http://localhost:7777", description="URL of Heidi CLI Server"
        )
        HEIDI_API_KEY: str = Field(
            default="", description="API Key for Heidi (required if server has HEIDI_API_KEY set)"
        )
        DEFAULT_EXECUTOR: str = Field(
            default="copilot", description="Default executor: copilot|jules|opencode|ollama"
        )
        DEFAULT_MODEL: str = Field(
            default="gpt-5",
            description="Copilot model to use (e.g., gpt-5, claude-sonnet-4-20250514)",
        )
        MAX_RETRIES: int = Field(default=2, description="Max re-plans after FAIL")

        # Copilot settings
        COPILOT_GH_TOKEN: str = Field(
            default="", description="GitHub token for Copilot (optional, uses gh auth if empty)"
        )

        # Jules settings
        ENABLE_JULES: bool = Field(default=False, description="Enable Jules CLI integration")
        JULES_API_KEY: str = Field(default="", description="Jules API Key (optional)")

        # OpenCode settings
        ENABLE_OPENCODE: bool = Field(default=False, description="Enable OpenCode CLI integration")
        OPENCODE_MODEL: str = Field(
            default="", description="OpenCode model (e.g., openai/gpt-4o). Leave empty for default."
        )

        # Ollama settings
        ENABLE_OLLAMA: bool = Field(default=False, description="Enable Ollama integration")
        OLLAMA_URL: str = Field(default="http://localhost:11434", description="Ollama server URL")
        OLLAMA_MODEL: str = Field(default="llama3", description="Ollama model name")

        REQUEST_TIMEOUT: int = Field(default=300, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()
        self._server_url = None
        self._agents_cache = None
        self._agents_cache_time = 0
        self._models_cache = None
        self._models_cache_time = 0

    @property
    def server_url(self) -> str:
        if self._server_url:
            return self._server_url
        return self.valves.HEIDI_SERVER_URL

    def _get_headers(self) -> dict:
        """Get request headers including API key if set."""
        headers = {"Content-Type": "application/json"}
        if self.valves.HEIDI_API_KEY:
            headers["X-Heidi-Key"] = self.valves.HEIDI_API_KEY
        return headers

    def _fetch_models(self) -> List[str]:
        """Fetch available Copilot models from Heidi server."""
        import time

        now = time.time()
        if self._models_cache and (now - self._models_cache_time) < 300:
            return self._models_cache

        try:
            url = f"{self.server_url}/models"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                if isinstance(models_data, list):
                    model_ids = [m.get("id", m.get("name", "")) for m in models_data]
                    self._models_cache = [m for m in model_ids if m]
                    self._models_cache_time = now
                    return self._models_cache
        except Exception:
            pass

        return COPILOT_MODELS

    def _get_executor_and_model(self, model_id: str = None) -> tuple:
        """Extract executor and model from model ID (e.g., 'copilot/gpt-5' -> ('copilot', 'gpt-5'))."""
        if not model_id:
            return self.valves.DEFAULT_EXECUTOR, self.valves.DEFAULT_MODEL

        if "/" in model_id:
            executor, model = model_id.split("/", 1)
            # Map executor names
            if executor == "opencode":
                return "opencode", model
            elif executor == "ollama":
                return "ollama", model
            elif executor == "jules":
                return "jules", model
            elif executor == "copilot":
                return "copilot", model

        return self.valves.DEFAULT_EXECUTOR, model_id or self.valves.DEFAULT_MODEL

    def _fetch_agents(self) -> List[tuple]:
        """Fetch agents from Heidi server."""
        import time

        # Cache agents for 5 minutes
        now = time.time()
        if self._agents_cache and (now - self._agents_cache_time) < 300:
            return self._agents_cache

        try:
            url = f"{self.server_url}/agents"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                agents_data = response.json()
                self._agents_cache = [
                    (a.get("name", "unknown"), a.get("description", "")) for a in agents_data
                ]
                self._agents_cache_time = now
                return self._agents_cache
        except Exception:
            pass

        # Fallback to default agents
        return [
            ("Plan", "Researches and outlines multi-step plans"),
            ("high-autonomy", "End-to-end autonomous engineer"),
            ("conservative-bugfix", "Fixes bugs with minimal changes"),
            ("reviewer-audit", "Audits tasks and repo state"),
            ("workflow-runner", "Orchestrates plan execution"),
            ("self-auditing", "Self-audits agent output before human review"),
        ]

    async def pipes(self):
        """Return available models from Copilot, Jules, and OpenCode."""
        import subprocess

        models = []

        # Fetch Copilot models from server
        try:
            url = f"{self.server_url}/models"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                copilot_models = response.json()
                if isinstance(copilot_models, list):
                    for m in copilot_models:
                        mid = m.get("id") or m.get("name", "")
                        if mid and not mid.startswith("error"):
                            models.append(
                                {
                                    "id": f"copilot/{mid}",
                                    "name": f"Copilot: {mid}",
                                }
                            )
        except Exception:
            pass

        # Fallback Copilot models if server unavailable
        if not models:
            for m in COPILOT_MODELS:
                models.append(
                    {
                        "id": f"copilot/{m}",
                        "name": f"Copilot: {m}",
                    }
                )

        # Fetch OpenCode models
        if self.valves.ENABLE_OPENCODE:
            try:
                result = subprocess.run(
                    ["opencode", "models", "openai"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        model_name = line.strip()
                        if model_name:
                            models.append(
                                {
                                    "id": f"opencode/{model_name}",
                                    "name": f"OpenCode: {model_name}",
                                }
                            )
            except Exception:
                pass

        # Add Ollama models if enabled
        if self.valves.ENABLE_OLLAMA:
            try:
                resp = requests.get(f"{self.valves.OLLAMA_URL}/api/tags", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for model in data.get("models", []):
                        model_name = model.get("name", "")
                        if model_name:
                            models.append(
                                {
                                    "id": f"ollama/{model_name}",
                                    "name": f"Ollama: {model_name}",
                                }
                            )
            except Exception:
                pass

        # Add placeholder for Jules (API-based, no model listing)
        if self.valves.ENABLE_JULES:
            models.append(
                {
                    "id": "jules/default",
                    "name": "Jules (uses default model)",
                }
            )

        return models

    async def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        """
        The main entry point for OpenWebUI Pipes (async).
        """
        try:
            # Get selected model from body
            selected_model = body.get("model", "")

            # Extract executor and model from selection
            executor, model = self._get_executor_and_model(selected_model)

            if "messages" not in body or not body["messages"]:
                return "No messages found"

            last_message = body["messages"][-1]["content"]

            if last_message.startswith("loop:"):
                task = last_message.replace("loop:", "").strip()
                return await self.execute_loop(task, executor=executor, model=model)

            if last_message.startswith("run:"):
                prompt = last_message.replace("run:", "").strip()
                return await self.execute_run(prompt, executor=executor, model=model)

            if last_message.startswith("agents"):
                return self.list_agents()

            if last_message.startswith("runs"):
                return await self.list_runs()

            return await self.chat_with_heidi(body["messages"], executor=executor, model=model)

        except Exception as e:
            traceback.print_exc()
            return f"**Heidi CLI Error**\n\n```\n{str(e)}\n```"

    def list_agents(self) -> str:
        """List available agents."""
        agents = self._fetch_agents()

        output = "### 🤖 Available Agents\n\n"
        output += "| Agent | Description |\n"
        output += "|-------|-------------|\n"
        for name, desc in agents:
            output += f"| **{name}** | {desc} |\n"

        return output

    async def execute_loop(self, task: str, executor: str = None, model: str = None) -> str:
        """Execute a full agent loop (Plan → Runner → Audit)."""
        executor = executor or self.valves.DEFAULT_EXECUTOR
        model = model or self.valves.DEFAULT_MODEL
        url = f"{self.server_url}/loop"
        payload = {
            "task": task,
            "executor": executor,
            "max_retries": self.valves.MAX_RETRIES,
            "model": model if executor == "copilot" else None,
        }
        payload = {k: v for k, v in payload.items() if v}

        try:
            response = requests.post(
                url, json=payload, headers=self._get_headers(), timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            run_id = data.get("run_id", "unknown")
            status = data.get("status", "unknown")
            result = data.get("result", "")
            error = data.get("error", "")

            output = "### 🔄 Agent Loop Started\n"
            output += f"**Task:** {task}\n"
            output += f"**Executor:** {self.valves.DEFAULT_EXECUTOR}\n"
            output += f"**Run ID:** {run_id}\n\n"

            if status == "completed":
                output += f"**Result:** {result}\n"
                output += "\n[View full logs: `heidi runs`]\n"
            else:
                output += f"**Status:** {status}\n"
                if error:
                    output += f"**Error:** {error}\n"

            return output

        except requests.exceptions.ConnectionError:
            return f"**Connection Error**\n\nCould not connect to Heidi server at {self.server_url}\n\nEnsure `heidi serve` is running."
        except requests.exceptions.Timeout:
            return f"**Timeout Error**\n\nRequest timed out after {self.valves.REQUEST_TIMEOUT}s.\n\nTry increasing REQUEST_TIMEOUT valve."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "**Authentication Error**\n\n401 Unauthorized.\n\nEnsure HEIDI_API_KEY valve is set correctly."
            return f"**HTTP Error**\n\n{str(e)}\n"
        except Exception as e:
            return f"**Heidi Loop Error**\n\n{str(e)}\n"

    async def execute_run(self, prompt: str, executor: str = None, model: str = None) -> str:
        """Execute a single prompt with the specified executor."""
        executor = executor or self.valves.DEFAULT_EXECUTOR
        model = model or self.valves.DEFAULT_MODEL
        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": executor,
            "model": model if executor == "copilot" else None,
        }
        payload = {k: v for k, v in payload.items() if v}

        try:
            response = requests.post(
                url, json=payload, headers=self._get_headers(), timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            run_id = data.get("run_id", "unknown")
            status = data.get("status", "unknown")
            result = data.get("result", "")
            error = data.get("error", "")

            output = "### ▶️ Run Started\n"
            output += f"**Prompt:** {prompt[:100]}...\n"
            output += f"**Executor:** {self.valves.DEFAULT_EXECUTOR}\n"
            output += f"**Run ID:** {run_id}\n\n"

            if status == "completed":
                output += f"**Output:**\n\n{result}\n"
            else:
                output += f"**Status:** {status}\n"
                if error:
                    output += f"**Error:** {error}\n"

            return output

        except requests.exceptions.ConnectionError:
            return f"**Connection Error**\n\nCould not connect to Heidi server at {self.server_url}\n\nEnsure `heidi serve` is running."
        except requests.exceptions.Timeout:
            return f"**Timeout Error**\n\nRequest timed out after {self.valves.REQUEST_TIMEOUT}s."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "**Authentication Error**\n\n401 Unauthorized.\n\nEnsure HEIDI_API_KEY valve is set correctly."
            return f"**HTTP Error**\n\n{str(e)}\n"
        except Exception as e:
            return f"**Heidi Run Error**\n\n{str(e)}\n"

    async def list_runs(self) -> str:
        """List recent runs."""
        url = f"{self.server_url}/runs"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            runs = response.json()

            if not runs:
                return "### 📋 Recent Runs\n\nNo runs found."

            output = "### 📋 Recent Runs\n\n"
            output += "| Run ID | Status | Task |\n"
            output += "|--------|--------|------|\n"
            for run in runs[:10]:
                task = run.get("task", run.get("prompt", ""))[:40]
                status = run.get("status", "unknown")
                output += f"| {run.get('run_id', 'N/A')} | {status} | {task}... |\n"

            return output

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "**Authentication Error**\n\n401 Unauthorized.\n\nEnsure HEIDI_API_KEY valve is set correctly."
            return f"**HTTP Error**\n\n{str(e)}\n"
        except Exception as e:
            return f"**Error listing runs**\n\n{str(e)}\n"
        return "**Error listing runs**\n"

    async def chat_with_heidi(
        self, messages: List[dict], executor: str = None, model: str = None
    ) -> str:
        """Route chat messages to Copilot via Heidi."""
        executor = executor or self.valves.DEFAULT_EXECUTOR
        model = model or self.valves.DEFAULT_MODEL
        prompt = "\n".join([m.get("content", "") for m in messages])

        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": executor,
            "model": model if executor == "copilot" else None,
        }
        payload = {k: v for k, v in payload.items() if v}

        try:
            response = requests.post(
                url, json=payload, headers=self._get_headers(), timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "completed":
                return data.get("result", "[No response]")
            else:
                return f"**Error:** {data.get('error', 'Unknown error')}\n"

        except requests.exceptions.ConnectionError:
            return f"**Connection Error**\n\nCould not connect to Heidi server at {self.server_url}\n\nEnsure `heidi serve` is running."
        except requests.exceptions.Timeout:
            return f"**Timeout Error**\n\nRequest timed out after {self.valves.REQUEST_TIMEOUT}s."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "**Authentication Error**\n\n401 Unauthorized.\n\nEnsure HEIDI_API_KEY valve is set correctly."
            return f"**HTTP Error**\n\n{str(e)}\n"
        except Exception as e:
            return f"**Heidi Chat Error**\n\n{str(e)}\n"


# For backward compatibility with old client
AGENTS_REGISTRY = {
    "Plan": {
        "description": "Researches and outlines multi-step plans",
        "role": "Architect",
    },
    "high-autonomy": {
        "description": "End-to-end autonomous engineer",
        "role": "Senior Engineer",
    },
    "conservative-bugfix": {
        "description": "Fixes bugs with minimal changes",
        "role": "Bug Fixer",
    },
    "reviewer-audit": {
        "description": "Audits tasks and repo state",
        "role": "QA / Auditor",
    },
    "workflow-runner": {
        "description": "Orchestrates plan execution",
        "role": "Manager",
    },
}
