from __future__ import annotations

import os
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
MAX_CONTEXT_SIZE = 400 * 1024  # 400KB


def should_ignore(path: Path) -> bool:
    return any(ignored in path.parts for ignored in IGNORE_DIRS)


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}


def is_text_file(path: Path) -> bool:
    return path.suffix in TEXT_EXTENSIONS


def collect_context(context_path: Path, max_size: int = MAX_CONTEXT_SIZE) -> str:
    if not context_path.exists():
        return ""

    if context_path.is_file():
        if is_text_file(context_path):
            content = context_path.read_text(encoding="utf-8", errors="ignore")
            return f"# {context_path.name}\n\n{content}\n"
        return ""

    contexts = []
    total_size = 0

    for root, dirs, files in os.walk(context_path):
        root_path = Path(root)
        if should_ignore(root_path):
            continue

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for f in files:
            if f in IGNORE_DIRS:
                continue

            # Optimization: Check extension on string to avoid expensive Path instantiation
            # for every file, which is significant for large projects.
            _, ext = os.path.splitext(f)
            if ext not in TEXT_EXTENSIONS:
                continue

            file_path = root_path / f
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if total_size + len(content) > max_size:
                    content = content[: max_size - total_size]
                    contexts.append(
                        f"# {file_path.relative_to(context_path)} (truncated)\n\n{content}\n"
                    )
                    break

                rel_path = file_path.relative_to(context_path)
                contexts.append(f"# {rel_path}\n\n{content}\n")
                total_size += len(content)
            except Exception:
                continue

    return "\n---\n".join(contexts)


def summarize_context(context: str, max_length: int = 2000) -> str:
    lines = context.split("\n")
    summary_lines = []
    current_size = 0

    for line in lines:
        if current_size + len(line) > max_length:
            summary_lines.append(f"... ({len(lines) - len(summary_lines)} more lines)")
            break
        summary_lines.append(line)
        current_size += len(line)

    return "\n".join(summary_lines)
