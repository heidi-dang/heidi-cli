from __future__ import annotations

import difflib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileChange:
    path: Path
    operation: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class WorkspaceSnapshot:
    git_root: Path
    files: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkspaceManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.git_root = self._find_git_root()

    def _find_git_root(self) -> Path:
        current = self.root
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return self.root

    def snapshot(self) -> WorkspaceSnapshot:
        snapshot = WorkspaceSnapshot(git_root=self.git_root)
        if not (self.git_root / ".git").exists():
            return snapshot

        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=self.git_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            files = result.stdout.strip("\x00").split("\x00")
            for f in files:
                if f:
                    try:
                        content = (self.git_root / f).read_text()
                        snapshot.files[f] = content
                    except Exception:
                        pass
        return snapshot

    def get_changed_files(self, snapshot: WorkspaceSnapshot) -> list[FileChange]:
        changes = []
        current_files: dict[str, str] = {}

        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=self.git_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            files = result.stdout.strip("\x00").split("\x00")
            for f in files:
                if f:
                    try:
                        content = (self.git_root / f).read_text()
                        current_files[f] = content
                    except Exception:
                        pass

        # New files
        for f, content in current_files.items():
            if f not in snapshot.files:
                changes.append(
                    FileChange(
                        path=Path(f),
                        operation="add",
                        new_content=content,
                    )
                )

        # Modified files
        for f, content in current_files.items():
            if f in snapshot.files and snapshot.files[f] != content:
                diff = "".join(
                    difflib.unified_diff(
                        snapshot.files[f].splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{f}",
                        tofile=f"b/{f}",
                    )
                )
                changes.append(
                    FileChange(
                        path=Path(f),
                        operation="modify",
                        old_content=snapshot.files[f],
                        new_content=content,
                        diff=diff,
                    )
                )

        # Deleted files
        for f in snapshot.files:
            if f not in current_files:
                changes.append(
                    FileChange(
                        path=Path(f),
                        operation="delete",
                        old_content=snapshot.files[f],
                    )
                )

        return changes


class PatchApplicator:
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/(?!\.)",
        r"dd\s+if=.*of=/dev/",
        r">\s*/dev/sd",
        r"format\s+.*drive",
    ]
    MAX_DIFF_SIZE = 100_000  # 100KB max diff size

    @classmethod
    def is_safe_diff(cls, diff: str) -> bool:
        if len(diff) > cls.MAX_DIFF_SIZE:
            return False
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, diff):
                return False
        return True

    @classmethod
    def apply_unified_diff(cls, diff: str, root: Path) -> list[FileChange]:
        changes = []
        lines = diff.splitlines()
        current_file = None
        old_lines: list[str] = []
        new_lines: list[str] = []

        for line in lines:
            if line.startswith("---"):
                if current_file and (old_lines or new_lines):
                    changes.append(cls._create_change(current_file, old_lines, new_lines))
                m = re.match(r"--- a/(.+)", line)
                if m:
                    current_file = m.group(1)
                    old_lines = []
                    new_lines = []
            elif line.startswith("+++"):
                pass
            elif line.startswith("@@"):
                pass
            elif line.startswith("-"):
                old_lines.append(line[1:] + "\n")
            elif line.startswith("+"):
                new_lines.append(line[1:] + "\n")

        if current_file and (old_lines or new_lines):
            changes.append(cls._create_change(current_file, old_lines, new_lines))

        for change in changes:
            if change.diff and not cls.is_safe_diff(change.diff):
                continue
            try:
                (root / change.path).write_text(change.new_content or "")
            except Exception:
                pass

        return changes

    @classmethod
    def _create_change(cls, path: str, old_lines: list[str], new_lines: list[str]) -> FileChange:
        old_content = "".join(old_lines)
        new_content = "".join(new_lines)
        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        return FileChange(
            path=Path(path),
            operation="modify" if old_content else "add",
            old_content=old_content or None,
            new_content=new_content or None,
            diff=diff,
        )


class VerificationRunner:
    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace

    def run_commands(self, commands: list[str], timeout: int = 60) -> dict[str, dict[str, str]]:
        results = {}
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.workspace.git_root,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=True,
                )
                results[cmd] = {
                    "returncode": str(result.returncode),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            except subprocess.TimeoutExpired:
                results[cmd] = {
                    "returncode": "-1",
                    "stdout": "",
                    "stderr": "Timeout",
                }
            except Exception as e:
                results[cmd] = {
                    "returncode": "-1",
                    "stdout": "",
                    "stderr": str(e),
                }
        return results
