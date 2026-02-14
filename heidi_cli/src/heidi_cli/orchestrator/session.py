from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..config import ConfigManager

class SessionState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    AUDITING = "auditing"
    FINISHED = "finished"
    FAILED = "failed"

@dataclass
class Session:
    session_id: str
    history: List[Dict[str, str]] = field(default_factory=list)
    state: SessionState = SessionState.IDLE
    plan: Optional[str] = None
    task: Optional[str] = None
    task_slug: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_message(self, role: str, content: str):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def set_state(self, new_state: SessionState):
        self.state = new_state
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def set_plan(self, plan: str):
        self.plan = plan
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def set_task(self, task: str, slug: str):
        self.task = task
        self.task_slug = slug
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def save(self):
        sessions_dir = ConfigManager.config_dir() / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        file_path = sessions_dir / f"{self.session_id}.json"

        data = {
            "session_id": self.session_id,
            "history": self.history,
            "state": self.state.value,
            "plan": self.plan,
            "task": self.task,
            "task_slug": self.task_slug,
            "artifacts": self.artifacts,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

        file_path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, session_id: str) -> Optional[Session]:
        sessions_dir = ConfigManager.config_dir() / "sessions"
        file_path = sessions_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return cls(
                session_id=data["session_id"],
                history=data.get("history", []),
                state=SessionState(data.get("state", "idle")),
                plan=data.get("plan"),
                task=data.get("task"),
                task_slug=data.get("task_slug"),
                artifacts=data.get("artifacts", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", "")
            )
        except Exception:
            return None

    @classmethod
    def create(cls) -> Session:
        session_id = str(uuid4())
        session = cls(session_id=session_id)
        session.save()
        return session
