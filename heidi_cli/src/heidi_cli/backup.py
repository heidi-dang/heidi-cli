from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import ConfigManager


def get_backup_dir(run_id: str) -> Path:
    backups_dir = ConfigManager.backups_dir()
    return backups_dir / run_id


def backup_file(file_path: Path, run_id: str) -> Optional[Path]:
    if not file_path.exists():
        return None
    
    backup_dir = get_backup_dir(run_id)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rel_path = file_path.name
    backup_path = backup_dir / f"{rel_path}.{timestamp}"
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def restore_file(file_path: Path, run_id: Optional[str] = None, latest: bool = True) -> bool:
    if file_path.exists():
        backup_file(file_path, "pre_restore")
    
    if run_id:
        backup_dir = get_backup_dir(run_id)
    else:
        backup_dir = ConfigManager.backups_dir()
    
    if not backup_dir.exists():
        return False
    
    pattern = file_path.name
    backups = sorted(backup_dir.glob(f"{pattern}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        return False
    
    target = backups[0] if latest else backups[-1]
    shutil.copy2(target, file_path)
    return True


def list_backups(run_id: Optional[str] = None) -> list[dict]:
    if run_id:
        backup_dir = get_backup_dir(run_id)
        if not backup_dir.exists():
            return []
        backups = list(backup_dir.iterdir())
    else:
        backups_dir = ConfigManager.backups_dir()
        if not backups_dir.exists():
            return []
        backups = []
        for rd in backups_dir.iterdir():
            if rd.is_dir():
                backups.extend(rd.iterdir())
    
    result = []
    for b in backups:
        if b.is_file():
            result.append({
                "path": str(b),
                "name": b.name,
                "size": b.stat().st_size,
                "modified": b.stat().st_mtime,
            })
    
    return sorted(result, key=lambda x: x["modified"], reverse=True)
