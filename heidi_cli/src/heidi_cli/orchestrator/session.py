from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from ..logging import redact_secrets
from ..config import ConfigManager
from .executors import pick_executor
from .plan import build_plan_prompt, extract_routing, parse_routing
from .registry import AgentRegistry
from .artifacts import TaskArtifact, sanitize_slug, save_audit_to_task, parse_audit_decision


@dataclass
class SessionState:
    id: str
    status: str = "AWAITING_TASK"  # AWAITING_TASK, PLANNING, WAITING_FOR_APPROVAL, EXECUTING, DONE, FAILED
    task: Optional[str] = None
    plan_text: Optional[str] = None
    routing: Optional[Dict[str, Any]] = None
    task_slug: Optional[str] = None
    workdir: Optional[str] = None
    planner_executor: str = "copilot"
    max_retries: int = 2
    retry_count: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class OrchestratorSession:
    """Stateful session for the Planner -> Runner -> Dev workflow."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_dir = ConfigManager.heidi_state_dir() / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.id = session_id
            self.state = self._load_state()
        else:
            self.id = f"sess_{os.urandom(4).hex()}"
            self.state = SessionState(id=self.id)
            self._save_state()

        self._lock = asyncio.Lock()

    def _load_state(self) -> SessionState:
        state_file = self.session_dir / f"{self.id}.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                return SessionState(**data)
            except Exception:
                pass
        return SessionState(id=self.id)

    def _save_state(self):
        state_file = self.session_dir / f"{self.id}.json"
        self.state.updated_at = datetime.utcnow().isoformat()
        state_file.write_text(json.dumps(asdict(self.state), indent=2))

    def _add_history(self, role: str, content: str):
        self.state.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self._save_state()

    async def handle_input(self, user_input: str) -> str:
        """Main entry point for user interaction."""
        async with self._lock:
            # Add user input to history
            self._add_history("user", user_input)

            if self.state.status == "AWAITING_TASK":
                return await self.initiate_plan(user_input)

            elif self.state.status == "PLANNING":
                # Should not happen usually, but if user interrupts
                return "I am currently generating a plan. Please wait."

            elif self.state.status == "WAITING_FOR_APPROVAL":
                if self._is_approval(user_input):
                    return await self.approve_plan()
                elif self._is_rejection(user_input):
                    return await self.reject_plan()
                else:
                    # Treat as feedback/modification request
                    return await self.modify_plan(user_input)

            elif self.state.status == "EXECUTING":
                # Queue or reject
                return "I am currently executing the approved plan. Please wait for completion or updates."

            elif self.state.status in ("DONE", "FAILED"):
                # New task
                self.state.status = "AWAITING_TASK"
                self._save_state()
                return await self.initiate_plan(user_input)

            return "Unknown state."

    def _is_approval(self, text: str) -> bool:
        t = text.lower().strip()
        return t in ("yes", "y", "approve", "ok", "go", "proceed", "looks good")

    def _is_rejection(self, text: str) -> bool:
        t = text.lower().strip()
        return t in ("no", "n", "reject", "stop", "cancel", "abort")

    async def initiate_plan(self, task: str) -> str:
        """Generate a plan for the task."""
        self.state.status = "PLANNING"
        self.state.task = task
        self.state.workdir = str(Path.cwd()) # Capture current workdir
        self._save_state()

        self._add_history("assistant", "Analyzing task and generating plan...")

        try:
            planner = pick_executor(self.state.planner_executor)
            prompt = build_plan_prompt(task)
            prompt += "\n\nIMPORTANT: In the routing YAML, you MUST specify 'executor: <name>' for each step. Choose from: copilot, jules, opencode, ollama. Default to 'copilot' if unsure."

            result = await planner.run(prompt, Path(self.state.workdir))

            if not result.ok:
                self.state.status = "AWAITING_TASK" # Reset
                msg = f"Planning failed: {result.output}"
                self._add_history("assistant", msg)
                return msg

            self.state.plan_text = result.output

            try:
                routing_text = extract_routing(result.output)
                self.state.routing = parse_routing(routing_text)
            except Exception as e:
                self.state.status = "AWAITING_TASK"
                msg = f"Failed to parse plan routing: {e}\n\nPlease try rephrasing the task."
                self._add_history("assistant", msg)
                return msg

            # Determine task slug
            match = re.search(r"^#\s*(.+?)$", result.output, re.MULTILINE)
            if match:
                self.state.task_slug = sanitize_slug(match.group(1))
            else:
                self.state.task_slug = sanitize_slug(task[:50])

            self.state.status = "WAITING_FOR_APPROVAL"
            self._save_state()

            msg = f"{self.state.plan_text}\n\nDo you approve this plan? (yes/no/feedback)"
            self._add_history("assistant", msg)
            return msg

        except Exception as e:
            self.state.status = "AWAITING_TASK"
            msg = f"Planning error: {str(e)}"
            self._add_history("assistant", msg)
            return msg

    async def modify_plan(self, feedback: str) -> str:
        """Regenerate plan with feedback."""
        self.state.status = "PLANNING"
        self._add_history("assistant", "Updating plan based on feedback...")

        try:
            planner = pick_executor(self.state.planner_executor)
            prompt = f"Original Task: {self.state.task}\n\nPrevious Plan:\n{self.state.plan_text}\n\nUser Feedback: {feedback}\n\nPlease generate a new, updated plan."
            prompt += "\n\nIMPORTANT: In the routing YAML, you MUST specify 'executor: <name>' for each step."

            result = await planner.run(prompt, Path(self.state.workdir))

            # Same parsing logic...
            if not result.ok:
                self.state.status = "WAITING_FOR_APPROVAL" # Revert to waiting state? Or reset?
                msg = f"Re-planning failed: {result.output}"
                self._add_history("assistant", msg)
                return msg

            self.state.plan_text = result.output
            try:
                routing_text = extract_routing(result.output)
                self.state.routing = parse_routing(routing_text)
            except Exception as e:
                # Keep status as PLANNING?
                msg = f"Failed to parse new plan: {e}"
                self._add_history("assistant", msg)
                return msg

            self.state.status = "WAITING_FOR_APPROVAL"
            self._save_state()

            msg = f"{self.state.plan_text}\n\nDo you approve this updated plan?"
            self._add_history("assistant", msg)
            return msg

        except Exception as e:
            msg = f"Error modifying plan: {e}"
            self._add_history("assistant", msg)
            return msg

    async def approve_plan(self) -> str:
        """Start execution."""
        self.state.status = "EXECUTING"
        self.state.retry_count = 0
        self._save_state()

        msg = "Plan approved. Starting execution..."
        self._add_history("assistant", msg)

        # Start execution in background (fire and forget from perspective of this call,
        # but we need to ensure the loop runs).
        # Since we are in an async function, we can create a task.
        asyncio.create_task(self._execute_workflow())

        return msg

    async def reject_plan(self) -> str:
        """Cancel planning."""
        self.state.status = "AWAITING_TASK"
        self.state.plan_text = None
        self.state.routing = None
        self._save_state()

        msg = "Plan rejected. What would you like to do next?"
        self._add_history("assistant", msg)
        return msg

    async def _execute_workflow(self):
        """Execute the approved workflow."""
        try:
            workdir = Path(self.state.workdir)

            # Create artifact
            artifact = TaskArtifact(slug=self.state.task_slug)
            artifact.content = f"# Task: {self.state.task}\n\n## Approved Plan\n{self.state.plan_text}\n"
            artifact.save()
            self.state.artifacts.append(str(artifact.path))

            all_passed = True

            # TODO: Refactor loop logic to be more modular here?
            # For now, implementing the core loop logic directly bound to session state

            batches = self.state.routing.get("execution_handoffs", [])

            # Validate executors first (Fail Fast)
            for batch in batches:
                exec_name = batch.get("executor", "copilot")
                try:
                    # Just try to pick it to see if it exists/is valid
                    pick_executor(exec_name)
                except Exception as e:
                    self.state.status = "FAILED"
                    msg = f"Configuration Error: Invalid executor '{exec_name}' in plan. {e}"
                    self._add_history("assistant", msg)
                    self._save_state()
                    return

            retry_loop = True
            while retry_loop:
                retry_loop = False # Reset flag
                all_batches_passed = True

                for batch in batches:
                    label = batch.get("label", "batch")
                    agent_name = batch.get("agent", "high-autonomy")
                    batch_executor = batch.get("executor", "copilot") # Default to copilot if missing

                    self._add_history("assistant", f"Running batch '{label}' using {batch_executor}...")

                    batch_exec = pick_executor(batch_executor)

                    prompt = f"""[BATCH: {label}]
[AGENT: {agent_name}]
TASK: {self.state.task}

You must implement the included steps: {batch.get("includes_steps")}
Verification commands: {batch.get("verification")}

IMPORTANT: When done, output DEV_COMPLETION block with:
- files_changed: [list of files]
- commands_run: [list of commands executed]
- results: [what was done]
"""
                    run_res = await batch_exec.run(prompt, workdir)

                    safe_output = redact_secrets(run_res.output)
                    artifact.content += f"\n## Batch: {label}\n\n### Output\n{safe_output[:2000]}\n"
                    artifact.save()

                    if not run_res.ok:
                        self._add_history("assistant", f"Batch '{label}' failed execution.")
                        all_batches_passed = False
                        break # Break batch loop

                    # Audit
                    reviewers = batch.get("reviewers", ["reviewer-audit"])
                    audit_passed = True

                    for reviewer in reviewers:
                        reviewer_agent = AgentRegistry.get(reviewer)
                        if not reviewer_agent:
                            continue

                        audit_prompt = f"""{reviewer_agent["prompt"]}
Task: {self.state.task}
Agent output:
{run_res.output}

IMPORTANT: Output exactly:
AUDIT_DECISION:
- status: PASS | FAIL
- why: "<short reason>"
END_AUDIT_DECISION
"""
                        # Use planner executor for audit usually, or safe default
                        # Using same batch executor for now unless specified otherwise?
                        # User requested audit might be "fixed to a safer/default executor".
                        # Let's use planner_executor for audit for consistency/safety.
                        audit_exec = pick_executor(self.state.planner_executor)

                        audit_res = await audit_exec.run(audit_prompt, workdir)
                        decision = parse_audit_decision(audit_res.output)

                        save_audit_to_task(self.state.task_slug, decision)

                        artifact.content += f"\n### Audit ({reviewer}): {decision.status}\n{decision.why}\n"
                        artifact.save()

                        if decision.status != "PASS":
                            audit_passed = False
                            self._add_history("assistant", f"Audit failed: {decision.why}")
                            break

                    if not audit_passed:
                        all_batches_passed = False
                        break # Break batch loop

                if not all_batches_passed:
                    self.state.retry_count += 1
                    if self.state.retry_count <= self.state.max_retries:
                        msg = f"Audit failed. Retrying ({self.state.retry_count}/{self.state.max_retries})..."
                        self._add_history("assistant", msg)
                        retry_loop = True # Loop again
                        continue
                    else:
                        self.state.status = "FAILED"
                        msg = f"Task failed after {self.state.max_retries} retries. Manual review required."
                        self._add_history("assistant", msg)
                        self._save_state()
                        return

            if all_passed:
                self.state.status = "DONE"
                msg = "Task completed successfully and passed all audits."
                self._add_history("assistant", msg)
                self._save_state()

        except Exception as e:
            self.state.status = "FAILED"
            msg = f"Workflow execution error: {str(e)}"
            self._add_history("assistant", msg)
            self._save_state()
