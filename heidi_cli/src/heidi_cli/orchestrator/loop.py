from __future__ import annotations

from pathlib import Path
from typing import Optional

from .executors import pick_executor
from .session import OrchestratorSession


def _pick_executor(name: str):
    return pick_executor(name)


async def run_loop(
    task: str,
    executor: str,
    model: Optional[str] = None,
    max_retries: int = 2,
    workdir: Path = None,
    dry_run: bool = False,
) -> str:
    """Execute Plan -> Runner -> Audit loop using OrchestratorSession.

    This function bridges the legacy CLI command `heidi loop` to the new persistent
    OrchestratorSession logic. It auto-approves the plan to maintain non-interactive behavior.
    """

    if dry_run:
        return "DRY_RUN: Not implemented for session-based loop yet."

    # Initialize a new session for this run
    session = OrchestratorSession()
    session.state.planner_executor = executor
    session.state.max_retries = max_retries
    if workdir:
        session.state.workdir = str(workdir)

    # 1. Initiate Plan
    print(f"Planning task with {executor}...")
    plan_msg = await session.initiate_plan(task)

    if session.state.status != "WAITING_FOR_APPROVAL":
        return f"FAIL: Planning failed.\n{plan_msg}"

    # 2. Auto-approve (Legacy CLI behavior)
    print("Plan generated. Auto-approving for execution...")
    await session.approve_plan()

    # 3. Wait for execution to complete
    # Since execute_workflow is a background task in session, we need to wait for it here
    # However, in session.py we fired it with create_task.
    # To make run_loop synchronous-wait, we should probably access the internal task or loop until done.

    import asyncio

    while session.state.status == "EXECUTING":
        await asyncio.sleep(1)

    # 1. Initiate Plan
    print(f"Planning task with {executor}...")
    plan_msg = await session.initiate_plan(task)

    if session.state.status != "WAITING_FOR_APPROVAL":
        return f"FAIL: Planning failed.\n{plan_msg}"

    # 2. Auto-approve (Legacy CLI behavior)
    print("Plan generated. Auto-approving for execution...")
    await session.approve_plan()

    # 3. Wait for execution to complete
    # Since execute_workflow is a background task in session, we need to wait for it here
    # However, in session.py we fired it with create_task.
    # To make run_loop synchronous-wait, we should probably access the internal task or loop until done.

    import asyncio

    while session.state.status == "EXECUTING":
        await asyncio.sleep(1)

    if session.state.status == "DONE":
        return "PASS"
    else:
        return f"FAIL: Execution ended with status {session.state.status}"
