from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .executors import (
    CopilotExecutor,
    OpenCodeExecutor,
    JulesExecutor,
    VscodeExecutor,
    OllamaExecutor,
    LMStudioExecutor,
)
from .plan import build_plan_prompt, extract_routing, parse_routing
from .registry import AgentRegistry
from .artifacts import TaskArtifact, sanitize_slug, save_audit_to_task
from ..logging import redact_secrets


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


def _pick_executor(name: str):
    return pick_executor(name)


@dataclass
class AuditDecision:
    status: str  # PASS or FAIL
    why: str = ""
    blocking_issues: list = None
    non_blocking: list = None
    rerun_commands: list = None
    recommended_next_step: str = ""

    def __post_init__(self):
        if self.blocking_issues is None:
            self.blocking_issues = []
        if self.non_blocking is None:
            self.non_blocking = []
        if self.rerun_commands is None:
            self.rerun_commands = []


def parse_audit_decision(text: str) -> AuditDecision:
    """Parse AUDIT_DECISION block from reviewer output."""
    decision = AuditDecision(status="FAIL", why="Could not parse audit decision")

    # Extract AUDIT_DECISION block
    match = re.search(r"AUDIT_DECISION:(.*?)(?:END_AUDIT_DECISION|$)", text, re.DOTALL)
    if not match:
        # Fall back to simple PASS/FAIL detection
        if "PASS" in text and "FAIL" not in text:
            decision.status = "PASS"
            decision.why = "PASS found in output"
            return decision
        elif "FAIL" in text:
            decision.status = "FAIL"
            decision.why = "FAIL found in output"
            return decision
        return decision

    block = match.group(1)

    # Parse status
    status_match = re.search(r"status:\s*(PASS|FAIL)", block, re.IGNORECASE)
    if status_match:
        decision.status = status_match.group(1).upper()

    # Parse why
    why_match = re.search(r"why:\s*(.+?)(?:\n|$)", block)
    if why_match:
        decision.why = why_match.group(1).strip()

    # Parse blocking_issues
    issues_match = re.search(r"blocking_issues:\s*(.+?)(?:\n\w|\Z)", block, re.DOTALL)
    if issues_match:
        issues_text = issues_match.group(1)
        decision.blocking_issues = [
            i.strip().lstrip("- ").strip() for i in issues_text.split("\n") if i.strip()
        ]

    # Parse non_blocking
    non_blocking_match = re.search(r"non_blocking:\s*(.+?)(?:\n\w|\Z)", block, re.DOTALL)
    if non_blocking_match:
        non_blocking_text = non_blocking_match.group(1)
        decision.non_blocking = [
            i.strip().lstrip("- ").strip() for i in non_blocking_text.split("\n") if i.strip()
        ]

    # Parse rerun_commands
    rerun_match = re.search(r"rerun_commands:\s*(.+?)(?:\n\w|\Z)", block, re.DOTALL)
    if rerun_match:
        rerun_text = rerun_match.group(1)
        decision.rerun_commands = [
            i.strip().lstrip("- ").strip() for i in rerun_text.split("\n") if i.strip()
        ]

    # Parse recommended_next_step
    next_step_match = re.search(r"recommended_next_step:\s*(.+?)(?:\n|\Z)", block)
    if next_step_match:
        decision.recommended_next_step = next_step_match.group(1).strip()

    return decision


def extract_task_slug(plan_output: str, default_task: str) -> str:
    """Extract task slug from Plan output title."""
    # Try to find a title in the plan output
    title_match = re.search(r"^#\s*(.+?)$", plan_output, re.MULTILINE)
    if title_match:
        return sanitize_slug(title_match.group(1))

    # Try to find "Plan:" in the output
    plan_title_match = re.search(r"Plan:\s*(.+?)(?:\n|$)", plan_output, re.MULTILINE)
    if plan_title_match:
        return sanitize_slug(plan_title_match.group(1))

    return sanitize_slug(default_task)


def build_task_content(task: str, plan_output: str, routing: dict, batch_output: str = "") -> str:
    """Build task.md content with required sections."""
    content = f"""# Task: {task}

## Goal
{task}

## Acceptance Criteria
"""

    # Extract acceptance criteria from plan if available
    if "Acceptance" in plan_output:
        acc_match = re.search(r"Acceptance[^\n]*\n(.*?)(?:\n##|\Z)", plan_output, re.DOTALL)
        if acc_match:
            content += acc_match.group(1).strip() + "\n"
    else:
        content += "See verification commands in routing.\n"

    content += """
## Steps Completed
"""

    # Extract steps from plan
    steps_match = re.search(r"Steps\s*\n(.*?)(?:\n\*\*|\n##|\Z)", plan_output, re.DOTALL)
    if steps_match:
        content += steps_match.group(1).strip() + "\n"
    else:
        content += "See routing YAML for execution order.\n"

    content += """
## Files Changed
"""

    # Try to extract files from DEV_COMPLETION
    files_match = re.search(r"files_changed:\s*(.+?)(?:\n|\Z)", batch_output, re.DOTALL)
    if files_match:
        content += files_match.group(1).strip() + "\n"
    else:
        content += "(See agent output)\n"

    content += """
## Commands Run + Outcomes
"""

    # Extract commands from DEV_COMPLETION
    commands_match = re.search(r"commands_run:\s*(.+?)(?:\n|\Z)", batch_output, re.DOTALL)
    if commands_match:
        content += commands_match.group(1).strip() + "\n"
    else:
        content += "(See agent output)\n"

    content += """
## Manual Checks
- (To be documented by reviewer)

## Risks + Rollback Notes
- (To be documented by reviewer)

## Open Questions
- None
"""

    return content


async def run_loop(
    task: str,
    executor: str,
    model: Optional[str] = None,
    max_retries: int = 2,
    workdir: Path = None,
    dry_run: bool = False,
) -> str:
    """Execute Plan -> Runner -> Audit loop with strict artifacts."""
    exec_impl = pick_executor(executor, model=model)

    task_slug = sanitize_slug(task)
    retry_count = 0

    # Create initial task artifact
    artifact = TaskArtifact(slug=task_slug)
    artifact.content = f"# {'DRY RUN - ' if dry_run else ''}Task: {task}\n\nCreated\n"
    artifact.save()

    while True:
        # 1) Plan
        plan_prompt = build_plan_prompt(task)
        plan_res = await exec_impl.run(plan_prompt, workdir)

        if not plan_res.ok:
            artifact.content += f"\n## Plan Failed\n{plan_res.output}"
            artifact.status = "failed"
            artifact.save()
            return f"FAIL: Plan step failed: {plan_res.output}"

        # Extract task_slug from plan output
        task_slug = extract_task_slug(plan_res.output, task)

        try:
            routing_text = extract_routing(plan_res.output)
            routing = parse_routing(routing_text)
        except Exception as e:
            artifact.content += f"\n## Routing Parse Error\n{e}\n\nRaw output:\n{plan_res.output}"
            artifact.status = "failed"
            artifact.save()
            return f"FAIL: Could not parse routing YAML: {e}\n\nRaw plan output:\n{plan_res.output}"

        # Save plan output to artifact
        artifact = TaskArtifact(slug=task_slug)
        artifact.content = build_task_content(task, plan_res.output, routing)
        if dry_run:
            artifact.content += "\n\n## DRY RUN\nExecution stopped at planning phase.\n"
        artifact.save()

        if dry_run:
            return "WAITING_FOR_APPROVAL: Plan generated. Run again without dry_run to execute."

        # 2) Execute each handoff with reviewer-audit
        all_batches_passed = True

        for batch in routing.get("execution_handoffs", []):
            label = batch.get("label", "batch")
            agent_name = batch.get("agent", "high-autonomy")
            batch_executor = batch.get("executor", executor)
            batch_exec = pick_executor(batch_executor)

            batch_prompt = f"""[BATCH: {label}]
[AGENT: {agent_name}]
TASK: {task}

You must implement the included steps: {batch.get("includes_steps")}
Verification commands: {batch.get("verification")}

IMPORTANT: When done, output DEV_COMPLETION block with:
- files_changed: [list of files]
- commands_run: [list of commands executed]
- results: [what was done]
"""

            # Run the agent
            run_res = await batch_exec.run(batch_prompt, workdir)

            # Redact secrets before storing
            safe_output = redact_secrets(run_res.output)

            if not run_res.ok:
                artifact.content += f"\n## Batch {label} Failed\n{run_res.output}"
                artifact.save()
                if retry_count >= max_retries:
                    artifact.status = "failed"
                    artifact.save()
                    return f"FAIL: Execution failed in {label}: {run_res.output}"
                all_batches_passed = False
                break

            # Check for DEV_COMPLETION markers - re-ask once if missing
            if "DEV_COMPLETION" not in run_res.output:
                run_res = await batch_exec.run(
                    batch_prompt
                    + "\n\nIMPORTANT: You MUST output DEV_COMPLETION markers when done.",
                    workdir,
                )
                safe_output = redact_secrets(run_res.output)

            # Update task content with batch output
            artifact.content += f"\n## Batch: {label}\n\n### Agent Output\n{safe_output[:2000]}"
            artifact.save()

            # Run self-auditing
            self_audit_agent = AgentRegistry.get("self-auditing")
            self_audit_passed = True
            if self_audit_agent:
                self_audit_prompt = (
                    f"{self_audit_agent['prompt']}\n\nYour output:\n{run_res.output}"
                )
                self_audit_res = await batch_exec.run(self_audit_prompt, workdir)
                self_audit_output = redact_secrets(self_audit_res.output)

                artifact.content += f"\n### Self-Audit\n{self_audit_output[:1000]}"
                artifact.save()

                if "SELF_AUDIT_FAIL" in self_audit_res.output:
                    self_audit_passed = False
                    artifact.content += "\n### Self-Audit: FAILED\n"
                    artifact.save()

            # Run reviewer-audit
            reviewers = batch.get("reviewers", ["reviewer-audit"])
            reviewer_passed = True
            for reviewer in reviewers:
                reviewer_agent = AgentRegistry.get(reviewer)
                if not reviewer_agent:
                    continue

                reviewer_prompt = f"""{reviewer_agent["prompt"]}

Task: {task}
Agent output:
{run_res.output}

IMPORTANT: Output exactly:

AUDIT_DECISION:
- status: PASS | FAIL
- why: "<short reason>"
- blocking_issues:
  - "<issue 1>"
- rerun_commands:
  - "<command if needed>"
- recommended_next_step: rerun_dev_batch:<label> | handoff_to_planner | accept_as_is
END_AUDIT_DECISION
"""
                audit_res = await batch_exec.run(reviewer_prompt, workdir)
                audit_output = redact_secrets(audit_res.output)

                artifact.content += f"\n### {reviewer} Review\n{audit_output[:2000]}"
                artifact.save()

                # Parse the audit decision
                decision = parse_audit_decision(audit_res.output)

                # Write audit to same task directory
                save_audit_to_task(task_slug, decision)

                if decision.status != "PASS":
                    reviewer_passed = False
                    artifact.content += f"\n### Review: FAILED - {decision.why}"
                    artifact.save()
                    break

            if not self_audit_passed or not reviewer_passed:
                all_batches_passed = False
                break

        # Check loop result
        if all_batches_passed:
            artifact.status = "passed"
            artifact.save()
            return "PASS"

        # Escalate to Plan for retry
        retry_count += 1
        if retry_count >= max_retries:
            artifact.status = "failed"
            artifact.content += (
                f"\n## FATAL ERROR\nExceeded max retries ({max_retries}). Execution stuck."
            )
            artifact.save()
            return f"FAIL: Exceeded max retries ({max_retries}). Execution stuck."

        # Continue loop to re-plan
        artifact.content += (
            f"\n## Retry {retry_count}/{max_retries}\nEscalating to Plan for new plan."
        )
        artifact.save()
