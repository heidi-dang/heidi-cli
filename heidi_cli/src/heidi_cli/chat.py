from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, List, Dict

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .orchestrator.executors import pick_executor, ExecResult
from .config import ConfigManager

console = Console()


class ChatSession:
    """Manages a multi-turn chat session with an executor."""

    def __init__(self, executor_name: str, model: Optional[str] = None):
        self.executor_name = executor_name
        self.model = model
        self.history: List[Dict[str, str]] = []
        self.session_id = f"chat_{os.urandom(4).hex()}"

        # Ensure config dir exists for history
        ConfigManager.ensure_dirs()
        self.history_file = ConfigManager.heidi_state_dir() / f"history_{self.executor_name}.json"
        self._load_history()

    def _load_history(self):
        """Load history from state file if exists."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                if isinstance(data, list):
                    self.history = data
            except Exception:
                pass

    def _save_history(self):
        """Save history to state file."""
        try:
            self.history_file.write_text(json.dumps(self.history, indent=2))
        except Exception:
            pass

    def reset(self):
        """Clear conversation history."""
        self.history = []
        if self.history_file.exists():
            self.history_file.unlink()

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._save_history()

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._save_history()

    def get_context_prompt(self, new_prompt: str) -> str:
        """Construct prompt with history context."""
        # For executors that don't support native history (like raw subprocesses),
        # we prepend context.
        # Note: Copilot/OpenAI/Ollama APIs usually handle history in messages list,
        # but our BaseExecutor interface currently takes a single string prompt.
        # We will format it as a conversation transcript for now.

        if not self.history:
            return new_prompt

        transcript = "Conversation History:\n"
        for msg in self.history[-10:]:  # Keep last 10 turns for context window
            role = "User" if msg["role"] == "user" else "Assistant"
            transcript += f"{role}: {msg['content']}\n\n"

        transcript += f"User: {new_prompt}\nAssistant:"
        return transcript

    async def send(self, prompt: str) -> str:
        """Send message and get response."""
        full_prompt = self.get_context_prompt(prompt)

        # Special handling for different executors if needed
        # But for now, we rely on the executor's ability to handle the transcript

        try:
            executor = pick_executor(self.executor_name, model=self.model)
            result: ExecResult = await executor.run(full_prompt, Path.cwd())

            if not result.ok:
                raise Exception(result.output)

            return result.output
        except Exception as e:
            return f"Error: {str(e)}"


async def start_chat_repl(executor_name: str, model: Optional[str] = None, reset: bool = False):
    """Start an interactive chat REPL."""
    session = ChatSession(executor_name, model)

    if reset:
        session.reset()
        console.print(f"[yellow]History cleared for {executor_name}.[/yellow]")

    console.print(
        Panel.fit(
            f"Starting chat with [bold cyan]{executor_name}[/bold cyan]"
            + (f" (model: {model})" if model else "")
            + "\nType 'exit' or 'quit' to end.\nType 'clear' or 'reset' to clear history.",
            title="Heidi Chat",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")

            if not user_input.strip():
                continue

            if user_input.lower() in ("exit", "quit"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() in ("clear", "reset"):
                session.reset()
                console.print("[yellow]History cleared.[/yellow]")
                continue

            session.add_user_message(user_input)

            with console.status(f"[bold cyan]{executor_name} is thinking...[/bold cyan]"):
                response = await session.send(user_input)

            session.add_assistant_message(response)

            console.print(f"[bold blue]{executor_name}[/bold blue]:")
            console.print(Markdown(response))
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
