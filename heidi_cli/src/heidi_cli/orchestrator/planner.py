from __future__ import annotations

import asyncio
from pathlib import Path

from .session import Session, SessionState
from .loop import pick_executor, execute_workflow, extract_task_slug
from .artifacts import TaskArtifact

class PlannerAgent:
    def __init__(self, session: Session):
        self.session = session

    async def process_user_message(self, message: str, workdir: Path = None):
        if not workdir:
            workdir = Path.cwd()

        self.session.add_message("user", message)

        if self.session.state == SessionState.WAITING_FOR_APPROVAL:
             # This should be handled by specific endpoints or logic, but if user types "approve", handle it.
             if message.strip().lower() == "approve":
                 return await self.approve_plan(workdir)
             elif message.strip().lower() == "reject":
                 return await self.reject_plan("Rejected by user.", workdir)
             else:
                 # Treat as feedback/modification request
                 self.session.set_state(SessionState.PLANNING)
                 # Fall through to planning logic

        if self.session.state in [SessionState.IDLE, SessionState.PLANNING, SessionState.FINISHED, SessionState.FAILED]:
            self.session.set_state(SessionState.PLANNING)

            # Construct prompt for Planner
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in self.session.history[-5:]]) # Last 5 messages

            system_prompt = f"""You are the Planner Agent for Heidi.
Your goal is to help the user by planning tasks or answering questions.

History:
{history_text}

Instructions:
- If this is a task request, create a detailed plan with steps, files to change, and verification steps.
- If this is a simple question, answer it.
- If you generated a plan and it is ready for execution, append "## APPROVE_REQUESTED" at the end of your response.
- If you need more information, ask the user.
"""

            executor = pick_executor("copilot")
            result = await executor.run(system_prompt, workdir)

            response_content = result.output
            self.session.add_message("planner", response_content)

            if "APPROVE_REQUESTED" in response_content:
                # Extract plan (everything before marker)
                plan_content = response_content.replace("## APPROVE_REQUESTED", "").strip()
                self.session.set_plan(plan_content)
                self.session.set_state(SessionState.WAITING_FOR_APPROVAL)

                # Extract slug consistent with execution logic
                slug = extract_task_slug(plan_content, message)
                self.session.set_task(message, slug=slug)
            else:
                self.session.set_state(SessionState.IDLE)

            return response_content

        return "Busy..."

    async def approve_plan(self, workdir: Path):
        if self.session.state != SessionState.WAITING_FOR_APPROVAL:
            return "No plan waiting for approval."

        self.session.set_state(SessionState.EXECUTING)
        self.session.add_message("system", "Plan approved. Starting execution...")

        asyncio.create_task(self._run_execution(workdir))
        return "Execution started."

    async def reject_plan(self, reason: str, workdir: Path):
        self.session.set_state(SessionState.IDLE)
        self.session.add_message("system", f"Plan rejected: {reason}")
        return f"Plan rejected: {reason}"

    async def _run_execution(self, workdir: Path):
        max_retries = 3
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Ensure artifact is ready and consistent
                if not self.session.task_slug:
                     self.session.task_slug = extract_task_slug(self.session.plan, self.session.task)
                     self.session.save()

                artifact = TaskArtifact.load(self.session.task_slug)
                if not artifact:
                     artifact = TaskArtifact(slug=self.session.task_slug)
                     artifact.content = f"# Task: {self.session.task}\n\nExecuting Plan...\n"
                     artifact.save()

                result = await execute_workflow(
                    self.session.task,
                    self.session.plan,
                    workdir,
                    artifact=artifact
                )

                if result.startswith("PASS"):
                     self.session.set_state(SessionState.FINISHED)
                     self.session.add_message("planner", f"Task completed successfully.\n\n{result}")
                     return

                # Failed
                retry_count += 1
                if retry_count > max_retries:
                     self.session.set_state(SessionState.FAILED)
                     self.session.add_message("planner", f"Task failed after {max_retries} attempts.\n\n{result}\nManual review required.")
                     return

                # Re-plan / Fix
                self.session.add_message("system", f"Execution failed (Attempt {retry_count}/{max_retries}). Requesting fix from Planner...")

                fix_prompt = f"""The execution of the plan failed.
Error/Result:
{result}

Please analyze the failure and provide an updated plan to fix the issues.
Current Plan:
{self.session.plan}

Output the new plan with ## APPROVE_REQUESTED at the end.
"""
                executor = pick_executor("copilot")
                fix_res = await executor.run(fix_prompt, workdir)

                if "APPROVE_REQUESTED" in fix_res.output:
                     new_plan = fix_res.output.replace("## APPROVE_REQUESTED", "").strip()
                     self.session.set_plan(new_plan)
                     self.session.add_message("planner", f"Updated plan for retry {retry_count}.\n\n{new_plan}")
                     # Loop continues to execute new plan
                else:
                     self.session.set_state(SessionState.FAILED)
                     self.session.add_message("planner", f"Planner failed to generate fix.\n\n{fix_res.output}")
                     return

            except Exception as e:
                self.session.set_state(SessionState.FAILED)
                self.session.add_message("system", f"Execution error: {str(e)}")
                return
