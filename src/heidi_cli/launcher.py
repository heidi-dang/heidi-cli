from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

from rich.console import Console
from .shared.config import ConfigLoader

console = Console()

def get_pids_file() -> Path:
    """Get the PID file path from suite data root."""
    config = ConfigLoader.load()
    pid_dir = config.data_root / "registry"
    pid_dir.mkdir(parents=True, exist_ok=True)
    return pid_dir / "pids.json"

def load_pids() -> Dict[str, int]:
    """Load PIDs from file."""
    pids_file = get_pids_file()
    if pids_file.exists():
        try:
            return json.loads(pids_file.read_text())
        except Exception:
            return {}
    return {}

def save_pids(pids: Dict[str, int]) -> None:
    """Save PIDs to file."""
    get_pids_file().write_text(json.dumps(pids, indent=2))

def add_pid(name: str, pid: int) -> None:
    """Add a PID to the tracking file."""
    pids = load_pids()
    pids[name] = pid
    save_pids(pids)

def remove_pid(name: str) -> None:
    """Remove a PID from the tracking file."""
    pids = load_pids()
    pids.pop(name, None)
    save_pids(pids)

def stop_process(name: str) -> bool:
    """Stop a managed process."""
    pids = load_pids()
    pid = pids.get(name)
    if not pid:
        return False
    
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        remove_pid(name)
        return True
    except OSError:
        remove_pid(name)
        return False

def start_daemon(name: str, cmd: list[str], log_name: str) -> int:
    """Start a command as a daemon process."""
    config = ConfigLoader.load()
    log_dir = config.data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / log_name
    log_fd = open(log_file, "w")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)

    process = subprocess.Popen(
        cmd,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )
    add_pid(name, process.pid)
    return process.pid
