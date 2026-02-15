from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Optional, Tuple

from rich.console import Console
from rich.progress import SpinnerColumn, TextColumn, Progress

from .config import ConfigManager

console = Console()


def ensure_ui_repo(ui_path: Optional[Path] = None, no_update: bool = False) -> Optional[Path]:
    """Ensure UI exists.

    If ui_path is None, uses heidi_ui_dir() (default cache location).
    If directory doesn't exist, shows error with install instructions.

    For development, use --ui-dir to point to local ui/ folder.

    Returns the Path to UI directory or None on failure.
    """
    from .config import heidi_ui_dir as _heidi_ui_dir

    if ui_path is None:
        ui_path = _heidi_ui_dir()

    ui_path = Path(ui_path)

    if not ui_path.exists():
        console.print(f"[red]UI not found at {ui_path}[/red]")
        console.print("")
        console.print("[yellow]To install UI, run:[/yellow]")
        console.print(
            "  curl -sSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash"
        )
        console.print("")
        console.print("[dim]Or for development, use --ui-dir to point to local ui/ folder:[/dim]")
        console.print("  heidi start ui --ui-dir /path/to/heidi-cli/ui")
        return None

    if no_update:
        console.print("[dim]Skipping UI update (--no-ui-update)[/dim]")
        return ui_path if ui_path.exists() else None

    # Check for bundled UI (from install.sh)
    # Try to update from cache (rsync-like behavior)
    console.print(f"[cyan]UI ready at {ui_path}[/cyan]")
    return ui_path


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the repo root by walking up for .git + heidi_cli or pyproject.toml."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        has_git = (current / ".git").exists()
        has_pyproject = (current / "pyproject.toml").exists()
        has_heidi = (current / "heidi_cli").exists() or (current / "ui").exists()

        if (has_git and has_heidi) or has_pyproject:
            return current
        current = current.parent

    has_git = (current / ".git").exists()
    has_pyproject = (current / "pyproject.toml").exists()
    has_heidi = (current / "heidi_cli").exists() or (current / "ui").exists()

    if (has_git and has_heidi) or has_pyproject:
        return current

    common_paths = [
        Path.home() / "heidi-cli",
        Path.home() / "dev" / "heidi-cli",
        Path.home() / "projects" / "heidi-cli",
        Path("/workspace/heidi-cli"),
    ]
    for path in common_paths:
        if (path / ".git").exists() and ((path / "heidi_cli").exists() or (path / "ui").exists()):
            return path

    return None


def get_heidi_dir() -> Path:
    """Get the global config directory path."""
    return ConfigManager.config_dir()


def get_pids_file() -> Path:
    """Get the PID file path."""
    return get_heidi_dir() / "pids.json"


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    logs_dir = get_heidi_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


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
    get_heidi_dir().mkdir(parents=True, exist_ok=True)
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


def wait_for_server(host: str, port: int, timeout: int = 15) -> bool:
    """Wait for server to be ready by polling /health endpoint."""
    start_time = time.time()
    url = f"http://{host}:{port}/health"

    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            time.sleep(0.5)

    return False


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def find_available_port(host: str, start_port: int = 7777, max_port: int = None) -> int:
    """Find an available port starting from start_port."""
    if max_port is None:
        max_port = start_port + 100
    port = start_port
    while port < max_port:
        if check_port_available(host, port):
            return port
        port += 1
    raise RuntimeError(f"Could not find available port between {start_port}-{max_port}")


def start_backend(
    host: str = "127.0.0.1",
    port: int = 7777,
    wait: bool = True,
    timeout: int = 15,
) -> Tuple[Optional[subprocess.Popen], int]:
    """
    Start the Heidi backend server.

    Returns (process, actual_port) tuple.
    """
    actual_port = port
    if not check_port_available(host, port):
        console.print(f"[yellow]Port {port} not available, finding available port...[/yellow]")
        actual_port = find_available_port(host, port)

    console.print(f"[cyan]Starting backend on {host}:{actual_port}...[/cyan]")

    env = os.environ.copy()
    env["HEIDI_NO_WIZARD"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "heidi_cli",
        "serve",
        "--host",
        host,
        "--port",
        str(actual_port),
    ]

    log_file = get_logs_dir() / "backend.log"
    log_fd = open(log_file, "w")

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    add_pid("backend", process.pid)

    if wait:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Waiting for backend to be ready...", total=None)
            if wait_for_server(host, actual_port, timeout):
                progress.update(task, completed=True)
                console.print(f"[green]Backend ready at http://{host}:{actual_port}[/green]")
            else:
                console.print(f"[red]Backend failed to start within {timeout}s[/red]")
                process.terminate()
                raise RuntimeError("Backend failed to start")

    return process, actual_port


def start_ui_dev_server(
    port: int = 3002,
    api_url: str = "http://localhost:7777",
    ui_dir: Optional[Path] = None,
) -> Optional[subprocess.Popen]:
    """
    Start the UI dev server via npm run dev.

    Returns the process.
    """
    if not check_port_available("127.0.0.1", port):
        console.print(
            f"[red]Port {port} is not available. Please free the port or use a different one.[/red]"
        )
        raise RuntimeError(f"Port {port} is not available")

    console.print(f"[cyan]Starting UI dev server on 127.0.0.1:{port}...[/cyan]")

    if ui_dir:
        ui_path = ui_dir
    else:
        repo_root = find_repo_root()
        if not repo_root:
            console.print("[red]Could not find repo root (no .git or pyproject.toml found)[/red]")
            console.print("[dim]Use --ui-dir to specify UI location[/dim]")
            return None
        ui_path = repo_root / "ui"

    if not ui_path.exists():
        console.print(f"[yellow]UI folder not found at {ui_path}[/yellow]")
        if not ui_dir:
            console.print(
                "[dim]Option 1: Clone UI with: git clone https://github.com/heidi-dang/Heidi-cli-ui ui[/dim]"
            )
            console.print("[dim]Option 2: Use --ui-dir to specify UI location[/dim]")
        return None

    if not (ui_path / "package.json").exists():
        console.print(
            f"[yellow]UI folder exists but missing package.json at {ui_path / 'package.json'}[/yellow]"
        )
        console.print("[dim]Run: git clone https://github.com/heidi-dang/heidi-cli-ui.git ui[/dim]")
        return None

    env = os.environ.copy()
    env["API_URL"] = api_url
    env["VITE_HEIDI_SERVER_BASE"] = api_url
    env["HEIDI_SERVER_BASE"] = api_url
    env["PORT"] = str(port)

    log_file = get_logs_dir() / "ui.log"
    log_fd = open(log_file, "w")

    process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(port), "--host", "127.0.0.1"],
        cwd=str(ui_path),
        env=env,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    add_pid("ui", process.pid)

    console.print(f"[green]UI dev server started on http://127.0.0.1:{port}[/green]")

    return process


def stop_process(pid: int) -> bool:
    """Stop a process by PID."""
    try:
        os.kill(pid, 15)
        time.sleep(1)
        try:
            os.kill(pid, 0)
            os.kill(pid, 9)
        except OSError:
            pass
        return True
    except OSError:
        return False


def stop_backend() -> None:
    """Stop the backend server."""
    pids = load_pids()
    if "backend" in pids:
        console.print(f"[cyan]Stopping backend (PID {pids['backend']})...[/cyan]")
        if stop_process(pids["backend"]):
            console.print("[green]Backend stopped[/green]")
        remove_pid("backend")


def stop_ui() -> None:
    """Stop the UI dev server."""
    pids = load_pids()
    if "ui" in pids:
        console.print(f"[cyan]Stopping UI (PID {pids['ui']})...[/cyan]")
        if stop_process(pids["ui"]):
            console.print("[green]UI stopped[/green]")
        remove_pid("ui")


def stop_all() -> None:
    """Stop all managed processes."""
    stop_backend()
    stop_ui()


def is_backend_running(host: str = "127.0.0.1", port: int = 7777) -> bool:
    """Check if backend is running."""
    try:
        urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2)
        return True
    except Exception:
        return False


def is_ui_running(port: int = 3002) -> bool:
    """Check if UI dev server is running by checking health endpoint."""
    import httpx

    try:
        response = httpx.get(f"http://127.0.0.1:{port}", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def get_status() -> Dict[str, dict]:
    """Get status of all managed services."""
    status = {}
    pids = load_pids()

    backend_running = is_backend_running()
    if "backend" in pids:
        try:
            os.kill(pids["backend"], 0)
            status["backend"] = {
                "pid": pids["backend"],
                "running": backend_running,
                "port": 7777,
            }
        except OSError:
            status["backend"] = {"pid": pids["backend"], "running": False, "port": 7777}
            remove_pid("backend")

    if "ui" in pids:
        try:
            os.kill(pids["ui"], 0)
            status["ui"] = {
                "pid": pids["ui"],
                "running": is_ui_running(),
                "port": 3002,
            }
        except OSError:
            status["ui"] = {"pid": pids["ui"], "running": False, "port": 3002}
            remove_pid("ui")

    return status
