"""
title: Heidi CLI Pipe
description: Control Copilot/Jules/OpenCode agents from OpenWebUI via Heidi CLI
author: Heidi
version: 2.0.0
"""

import requests
import traceback
from pydantic import BaseModel, Field
from typing import List, Union, Generator, Iterator


class Pipe:
    class Valves(BaseModel):
        HEIDI_SERVER_URL: str = Field(
            default="http://localhost:7777",
            description="URL of Heidi CLI Server"
        )
        HEIDI_API_TOKEN: str = Field(default="", description="API Token for Heidi (optional)")
        DEFAULT_EXECUTOR: str = Field(default="copilot", description="Default executor: copilot|jules|opencode")
        DEFAULT_AGENT: str = Field(default="high-autonomy", description="Default agent to use")
        MAX_RETRIES: int = Field(default=2, description="Max re-plans after FAIL")
        ENABLE_JULES: bool = Field(default=False, description="Enable Jules CLI integration")
        ENABLE_OPENCODE: bool = Field(default=False, description="Enable OpenCode CLI integration")

    def __init__(self):
        self.valves = self.Valves()
        self._server_url = None

    @property
    def server_url(self) -> str:
        if self._server_url:
            return self._server_url
        return self.valves.HEIDI_SERVER_URL

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        """
        The main entry point for OpenWebUI Pipes.
        """
        try:
            if "messages" not in body or not body["messages"]:
                return "No messages found"

            last_message = body["messages"][-1]["content"]

            if last_message.startswith("loop:"):
                task = last_message.replace("loop:", "").strip()
                return self.execute_loop(task)

            if last_message.startswith("run:"):
                prompt = last_message.replace("run:", "").strip()
                return self.execute_run(prompt)

            if last_message.startswith("agents"):
                return self.list_agents()

            if last_message.startswith("runs"):
                return self.list_runs()

            return self.chat_with_heidi(body["messages"])

        except Exception as e:
            traceback.print_exc()
            return f"**Heidi CLI Error**\n\n```\n{str(e)}\n```"

    def execute_loop(self, task: str) -> str:
        """Execute a full agent loop (Plan → Runner → Audit)."""
        url = f"{self.server_url}/loop"
        payload = {
            "task": task,
            "executor": self.valves.DEFAULT_EXECUTOR,
            "max_retries": self.valves.MAX_RETRIES,
        }

        try:
            response = requests.post(url, json=payload, timeout=300)
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
        except Exception as e:
            return f"**Heidi Loop Error**\n\n{str(e)}\n"

    def execute_run(self, prompt: str) -> str:
        """Execute a single prompt with the specified executor."""
        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": self.valves.DEFAULT_EXECUTOR,
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
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
        except Exception as e:
            return f"**Heidi Run Error**\n\n{str(e)}\n"

    def list_agents(self) -> str:
        """List available agents."""
        agents = [
            ("Plan", "Researches and outlines multi-step plans"),
            ("high-autonomy", "End-to-end autonomous engineer"),
            ("conservative-bugfix", "Fixes bugs with minimal changes"),
            ("reviewer-audit", "Audits tasks and repo state"),
            ("workflow-runner", "Orchestrates plan execution"),
            ("self-auditing", "Self-audits agent output before human review"),
        ]

        output = "### 🤖 Available Agents\n\n"
        output += "| Agent | Description |\n"
        output += "|-------|-------------|\n"
        for name, desc in agents:
            output += f"| **{name}** | {desc} |\n"

        return output

    def list_runs(self) -> str:
        """List recent runs."""
        url = f"{self.server_url}/runs"
        try:
            response = requests.get(url, timeout=10)
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

        except Exception as e:
            return f"**Error listing runs**\n\n{str(e)}\n"

    def chat_with_heidi(self, messages: List[dict]) -> str:
        """Route chat messages to Copilot via Heidi."""
        prompt = "\n".join([m.get("content", "") for m in messages])

        url = f"{self.server_url}/run"
        payload = {
            "prompt": prompt,
            "executor": self.valves.DEFAULT_EXECUTOR,
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "completed":
                return data.get("result", "[No response]")
            else:
                return f"**Error:** {data.get('error', 'Unknown error')}\n"

        except requests.exceptions.ConnectionError:
            return f"**Connection Error**\n\nCould not connect to Heidi server at {self.server_url}\n\nEnsure `heidi serve` is running."
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
