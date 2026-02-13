from __future__ import annotations

import os
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
MAX_CONTEXT_SIZE = 400 * 1024  # 400KB


def should_ignore(path: Path) -> bool:
    return any(ignored in path.parts for ignored in IGNORE_DIRS)


def is_text_file(path: Path) -> bool:
    text_extensions = {".md", ".txt", ".rst", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
    return path.suffix in text_extensions


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
        
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
        
        for f in files:
            file_path = root_path / f
            if should_ignore(file_path):
                continue
            
            if not is_text_file(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if total_size + len(content) > max_size:
                    content = content[: max_size - total_size]
                    contexts.append(f"# {file_path.relative_to(context_path)} (truncated)\n\n{content}\n")
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
