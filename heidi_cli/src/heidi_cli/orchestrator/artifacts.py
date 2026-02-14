from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import ConfigManager
from ..logging import HeidiLogger, redact_secrets


@dataclass
class TaskArtifact:
    slug: str
    content: str = ""
    audit_content: str = ""
    progress_content: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def save(self) -> Path:
        tasks_dir = ConfigManager.tasks_dir()
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / f"{self.slug}.md"
        audit_file = tasks_dir / f"{self.slug}.audit.md"

        task_file.write_text(redact_secrets(self.content))
        audit_file.write_text(redact_secrets(self.audit_content))

        meta = {
            "slug": self.slug,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": datetime.utcnow().isoformat(),
        }
        (tasks_dir / f"{self.slug}.meta.json").write_text(json.dumps(meta, indent=2))

        return tasks_dir

    @classmethod
    def load(cls, slug: str) -> Optional[TaskArtifact]:
        tasks_dir = ConfigManager.tasks_dir()
        if not tasks_dir.exists():
            return None

        meta_file = tasks_dir / f"{slug}.meta.json"
        if not meta_file.exists():
            return None

        meta = json.loads(meta_file.read_text())
        task_file = tasks_dir / f"{slug}.md"
        audit_file = tasks_dir / f"{slug}.audit.md"

        content = task_file.read_text() if task_file.exists() else ""
        audit = audit_file.read_text() if audit_file.exists() else ""

        return cls(
            slug=slug,
            content=content,
            audit_content=audit,
            status=meta.get("status", "pending"),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", ""),
        )


def sanitize_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", text.lower())
    slug = re.sub(r"_+", "_", slug)
    return slug[:50]


def create_task_artifact(task: str) -> TaskArtifact:
    slug = sanitize_slug(task)
    artifact = TaskArtifact(
        slug=slug, content=f"# Task: {task}\n\nCreated: {datetime.utcnow().isoformat()}\n"
    )
    artifact.save()
    HeidiLogger.write_event("task_created", {"slug": slug, "task": task})
    return artifact


def update_task_progress(slug: str, progress: str) -> None:
    artifact = TaskArtifact.load(slug)
    if artifact:
        artifact.progress_content += f"\n{datetime.utcnow().isoformat()}: {progress}"
        artifact.save()
        HeidiLogger.write_event("progress_update", {"slug": slug, "progress": progress})


def update_task_audit(slug: str, audit_result: str, passed: bool) -> None:
    artifact = TaskArtifact.load(slug)
    if artifact:
        artifact.audit_content += (
            f"\n{datetime.utcnow().isoformat()} - {'PASS' if passed else 'FAIL'}: {audit_result}"
        )
        artifact.status = "passed" if passed else "failed"
        artifact.save()
        HeidiLogger.write_event(
            "audit_update", {"slug": slug, "passed": passed, "result": audit_result}
        )


def save_audit_to_task(slug: str, decision) -> None:
    """Save audit decision to the task audit file."""
    tasks_dir = ConfigManager.tasks_dir()
    tasks_dir.mkdir(parents=True, exist_ok=True)

    content = f"""# Audit: {slug}

## Decision
Status: {decision.status}
Why: {decision.why}

## Blocking Issues
{chr(10).join(f"- {i}" for i in decision.blocking_issues) if decision.blocking_issues else "None"}

## Non-Blocking
{chr(10).join(f"- {i}" for i in decision.non_blocking) if decision.non_blocking else "None"}

## Recommended Next Step
{decision.recommended_next_step}

## Timestamp
{datetime.utcnow().isoformat()}
"""
    audit_file = tasks_dir / f"{slug}.audit.md"
    audit_file.write_text(redact_secrets(content))
