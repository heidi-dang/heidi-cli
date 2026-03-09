from __future__ import annotations

import typer
import sys
from rich.console import Console

from .shared.config import ConfigLoader
from .launcher import start_daemon, stop_process, load_pids

console = Console()
app = typer.Typer(
    add_completion=False,
    help="Heidi Unified Learning Suite CLI",
)

# New Module Sub-apps
model_app = typer.Typer(help="Local model management (serve/status/stop/reload)")
memory_app = typer.Typer(help="Memory management (status/search)")
learning_app = typer.Typer(help="Learning & Training management (reflect/export/curate/train-full/eval/promote/rollback)")

app.add_typer(model_app, name="model")
app.add_typer(memory_app, name="memory")
app.add_typer(learning_app, name="learning")

@app.command()
def status():
    """Show suite status."""
    config = ConfigLoader.load()
    console.print("[bold]Learning Suite Status[/bold]")
    console.print(f"Suite Enabled: {config.suite_enabled}")
    console.print(f"Data Root: {config.data_root}")
    console.print(f"Model Host: {config.host}:{config.port} (Enabled: {config.model_host_enabled})")
    
    pids = load_pids()
    if "model_host" in pids:
        console.print(f"Model Host PID: [green]{pids['model_host']}[/green]")
    else:
        console.print("Model Host PID: [red]Not running[/red]")

@app.command()
def doctor():
    """Run suite verification checks."""
    from pathlib import Path
    
    # Locate the doctor script and run its main logic
    doctor_script = Path(__file__).parent.parent.parent / "scripts" / "doctor.py"
    if doctor_script.exists():
        # Read and execute the script in the current environment
        namespace = {"__file__": str(doctor_script)}
        # Ensure we don't accidentally recursively import cli
        exec(doctor_script.read_text(), namespace)
        if "run_doctor" in namespace:
            namespace["run_doctor"]()
        elif "check_all" in namespace:
            namespace["check_all"]()
    else:
        console.print(f"[red]Doctor script not found at {doctor_script}[/red]")

@model_app.command("serve")
def model_serve():
    """Start local model host daemon."""
    config = ConfigLoader.load()
    if not config.model_host_enabled:
        console.print("[red]Model host is disabled in config.[/red]")
        raise typer.Exit(1)
    
    pids = load_pids()
    if "model_host" in pids:
        console.print(f"[yellow]Model host already running (PID: {pids['model_host']})[/yellow]")
        return

    console.print(f"Starting model host on {config.host}:{config.port}...")
    
    # Command to run uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn", "heidi_cli.model_host.server:app",
        "--host", config.host,
        "--port", str(config.port)
    ]
    
    pid = start_daemon("model_host", cmd, "model_host.log")
    console.print(f"[green]✓ Model host started (PID: {pid})[/green]")
    console.print(f"Logs: {config.data_root / 'logs' / 'model_host.log'}")

@model_app.command("status")
def model_status():
    """Check local model host status."""
    pids = load_pids()
    if "model_host" in pids:
        console.print(f"[green]Model host is running (PID: {pids['model_host']})[/green]")
    else:
        console.print("[red]Model host is not running.[/red]")

@model_app.command("stop")
def model_stop():
    """Stop local model host daemon."""
    if stop_process("model_host"):
        console.print("[green]✓ Model host stopped.[/green]")
    else:
        console.print("[yellow]Model host was not running.[/yellow]")

@memory_app.command("status")
def memory_status():
    """Show memory database status."""
    from .runtime.db import db
    conn = db.get_connection()
    counts = {
        "memories": conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
        "reflections": conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0],
        "rules": conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0],
        "episodes": conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
    }
    console.print("[bold]Memory Database Status[/bold]")
    for table, count in counts.items():
        console.print(f" {table.capitalize()}: {count}")

@learning_app.command("reflect")
def learning_reflect(run_id: str, task: str, outcome: str):
    """Manually trigger reflection on a run."""
    import asyncio
    from .runtime.reflection import reflection_engine
    console.print(f"Reflecting on run {run_id}...")
    ref_id = asyncio.run(reflection_engine.reflect_on_run(run_id, task, outcome))
    console.print(f"[green]✓ Reflection created: {ref_id}[/green]")

@learning_app.command("export")
def learning_export(run_id: str):
    """(Phase 3 WIP) Export a run for manual review."""
    console.print(f"Exporting run {run_id} (Not implemented in Phase 3 skeleton)")

@learning_app.command("curate")
def learning_curate(date: Optional[str] = None):
    """Curate raw runs into redacted training datasets."""
    import asyncio
    from .pipeline.curation import curation_engine
    console.print(f"Curating dataset (Filter: {date or 'All'})...")
    count = asyncio.run(curation_engine.curate_dataset(date))
    console.print(f"[green]✓ Curated {count} runs into a new dataset.[/green]")

if __name__ == "__main__":
    app()
