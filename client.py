"""
title: Heidi CLI Pipe
description: Control Copilot/Jules/OpenCode agents from OpenWebUI via Heidi CLI
author: Heidi
version: 2.0.0
"""

import traceback
from typing import List, Union, Generator, Iterator

import requests
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        HEIDI_SERVER_URL: str = Field(
            default="http://localhost:7777", description="URL of Heidi CLI Server"
        )
        HEIDI_API_KEY: str = Field(
            default="", description="API Key for Heidi (required if server has HEIDI_API_KEY set)"
        )
        DEFAULT_EXECUTOR: str = Field(
            default="copilot", description="Default executor: copilot|jules|opencode"
        )
        DEFAULT_AGENT: str = Field(default="high-autonomy", description="Default agent to use")
        MAX_RETRIES: int = Field(default=2, description="Max re-plans after FAIL")
        ENABLE_JULES: bool = Field(default=False, description="Enable Jules CLI integration")
        ENABLE_OPENCODE: bool = Field(default=False, description="Enable OpenCode CLI integration")
        REQUEST_TIMEOUT: int = Field(default=300, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()
        self._server_url = None
        self._agents_cache = None
        self._agents_cache_time = 0

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

    async def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        """
        The main entry point for OpenWebUI Pipes (async).
        """
        try:
            if "messages" not in body or not body["messages"]:
                return "No messages found"

            last_message = body["messages"][-1]["content"]

            if last_message.startswith("loop:"):
                task = last_message.replace("loop:", "").strip()
                return await self.execute_loop(task)

            if last_message.startswith("run:"):
                prompt = last_message.replace("run:", "").strip()
                return await self.execute_run(prompt)

            if last_message.startswith("agents"):
                return self.list_agents()

            if last_message.startswith("runs"):
                return await self.list_runs()

            return await self.chat_with_heidi(body["messages"])

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

    async def execute_loop(self, task: str) -> str:
        """Execute a full agent loop (Plan → Runner → Audit)."""
        url = f"{self.server_url}/loop"
        payload = {
            "task": task,
            "executor": self.valves.DEFAULT_EXECUTOR,
            "max_retries": self.valves.MAX_RETRIES,
        }

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

    async def execute_run(self, prompt: str) -> str:
        """Execute a single prompt with the specified executor."""
        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": self.valves.DEFAULT_EXECUTOR,
        }

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

    async def chat_with_heidi(self, messages: List[dict]) -> str:
        """Route chat messages to Copilot via Heidi."""
        prompt = "\n".join([m.get("content", "") for m in messages])

        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": self.valves.DEFAULT_EXECUTOR,
        }

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
