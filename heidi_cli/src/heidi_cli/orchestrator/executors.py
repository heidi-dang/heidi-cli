from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..copilot_runtime import CopilotRuntime


@dataclass
class ExecResult:
    ok: bool
    output: str
    events: list[dict[str, Any]] = None

    def __post_init__(self):
        if self.events is None:
            self.events = []  # type: ignore[assignment]


class BaseExecutor:
    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        raise NotImplementedError


class CopilotExecutor(BaseExecutor):
    def __init__(self, model: Optional[str] = None, cwd: Optional[Path] = None):
        self.model = model
        self.cwd = cwd

    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        rt = CopilotRuntime(model=self.model, cwd=workdir or self.cwd)
        await rt.start()
        try:
            text = await rt.send_and_wait(f"WORKDIR: {workdir}\n\n{prompt}")
            return ExecResult(ok=True, output=text)
        except Exception as e:
            return ExecResult(ok=False, output=str(e))
        finally:
            await rt.stop()


class SubprocessExecutor(BaseExecutor):
    def __init__(self, cmd_prefix: list[str]):
        self.cmd_prefix = cmd_prefix

    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        cmd = self.cmd_prefix + [prompt]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        text = (out or b"").decode(errors="replace")
        return ExecResult(ok=(proc.returncode == 0), output=text)


class OpenCodeExecutor(SubprocessExecutor):
    def __init__(self):
        super().__init__(["opencode", "run"])


class JulesExecutor(SubprocessExecutor):
    def __init__(self):
        super().__init__(["jules", "remote", "new"])


class VscodeExecutor(BaseExecutor):
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port

    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                "code",
                "--folder-uri",
                f"vscode-remote://localhost+{workdir}",
                "--command",
                "heidi-vscode.execute",
                "--",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await proc.communicate()
            text = (out or b"").decode(errors="replace")
            return ExecResult(ok=(proc.returncode == 0), output=text)
        except FileNotFoundError:
            return ExecResult(ok=False, output="VS Code not found in PATH")


class OllamaExecutor(BaseExecutor):
    def __init__(self, model: str = "llama3", url: str = "http://localhost:11434"):
        self.model = model
        self.url = url

    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return ExecResult(ok=True, output=data.get("response", ""))
                    else:
                        return ExecResult(ok=False, output=f"Ollama error: {resp.status}")
        except Exception as e:
            return ExecResult(ok=False, output=f"Failed to connect to Ollama: {e}")


class LMStudioExecutor(BaseExecutor):
    def __init__(self, model: str = "llama3", url: str = "http://localhost:1234/v1"):
        self.model = model
        self.url = url

    async def run(self, prompt: str, workdir: Path) -> ExecResult:
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return ExecResult(ok=True, output=data["choices"][0]["message"]["content"])
                    else:
                        return ExecResult(ok=False, output=f"LM Studio error: {resp.status}")
        except Exception as e:
            return ExecResult(ok=False, output=f"Failed to connect to LM Studio: {e}")

def pick_executor(name: str, model: Optional[str] = None):
    name = (name or "copilot").lower()
    if name == "copilot":
        return CopilotExecutor(model=model)
    if name == "opencode":
        return OpenCodeExecutor()
    if name == "jules":
        return JulesExecutor()
    if name == "vscode":
        return VscodeExecutor()
    if name == "ollama":
        return OllamaExecutor()
    if name == "lmstudio":
        return LMStudioExecutor()
    if name == "local":
        return OllamaExecutor()
    raise ValueError(f"Unknown executor: {name}")
