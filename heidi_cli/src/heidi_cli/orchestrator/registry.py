from __future__ import annotations

from typing import Optional

from ..config import ConfigManager

DEFAULT_AGENTS: dict[str, dict[str, str]] = {
    "Plan": {
        "description": "Researches and outlines multi-step plans",
        "role": "Architect",
        "prompt": """You are the Plan agent.
Return:
1) A numbered plan (Steps 1..N)
2) A routing YAML block between markers:

BEGIN_EXECUTION_HANDOFFS_YAML
execution_handoffs:
  - label: "Batch 1"
    agent: "high-autonomy"
    includes_steps: [1, 2]
    reviewers: ["reviewer-audit"]
    verification:
      - "git status"
    executor: "copilot"
END_EXECUTION_HANDOFFS_YAML

Always include the YAML markers. If you cannot produce valid YAML, the task will FAIL automatically.
""",
    },
    "high-autonomy": {
        "description": "End-to-end autonomous engineer",
        "role": "Senior Engineer",
        "prompt": """You are a high-autonomy engineer. Implement the task end-to-end.
When done, output:

DEV_COMPLETION
- changed_files: [list of files changed]
- summary: [what was done]
- verification_commands: [commands run to verify]
DEV_COMPLETION
""",
    },
    "reviewer-audit": {
        "description": "Audits tasks and repo state",
        "role": "QA / Auditor",
        "prompt": """You are a strict auditor. Examine the task output and repository state.
Output exactly:

PASS: [brief reason]

or

FAIL: [brief reason and what needs fixing]

Be strict. Only pass if verification commands succeeded.
""",
    },
    "self-auditing": {
        "description": "Self-audits agent output before human review",
        "role": "Automated QA",
        "prompt": """You are a self-auditing agent. Review your own output before completing.
Check:
1. Did you produce DEV_COMPLETION markers?
2. Are changed files listed?
3. Did verification commands succeed?
4. Is the code syntactically correct?

Output:
SELF_AUDIT_PASS: [summary]
or
SELF_AUDIT_FAIL: [issues found]
""",
    },
    "workflow-runner": {
        "description": "Executes batches from routing YAML",
        "role": "Orchestrator",
        "prompt": """You are the workflow runner. Execute batches in order.
For each batch:
1. Parse the agent and includes_steps
2. Run the agent with appropriate prompt
3. Collect results
4. Move to next batch

Report final status.
""",
    },
}


class AgentRegistry:
    _agents: dict[str, dict[str, str]] = {}

    @classmethod
    def load(cls) -> dict[str, dict[str, str]]:
        if cls._agents:
            return cls._agents

        cls._agents = DEFAULT_AGENTS.copy()

        agents_dir = ConfigManager.heidi_dir() / "agents"
        if agents_dir.exists():
            for md_file in agents_dir.glob("*.md"):
                agent_name = md_file.stem
                content = md_file.read_text()
                cls._agents[agent_name] = {
                    "description": f"Loaded from {md_file.name}",
                    "role": "Custom",
                    "prompt": content,
                }

        return cls._agents

    @classmethod
    def get(cls, name: str) -> Optional[dict[str, str]]:
        agents = cls.load()
        return agents.get(name)

    @classmethod
    def list_agents(cls) -> list[tuple[str, str]]:
        agents = cls.load()
        return [(name, info.get("description", "")) for name, info in agents.items()]

    @classmethod
    def validate_required(cls) -> list[str]:
        required = ["Plan", "workflow-runner", "reviewer-audit", "self-auditing"]
        agents = cls.load()
        missing = [r for r in required if r not in agents]
        return missing


AGENTS_REGISTRY = AgentRegistry._agents
