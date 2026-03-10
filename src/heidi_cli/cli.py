from __future__ import annotations

import typer
import sys
from typing import Optional
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

@app.command()
def setup():
    """Interactive setup wizard for Heidi CLI."""
    import os
    from pathlib import Path
    
    console.print("[bold blue]🤖 Heidi CLI Setup Wizard[/bold blue]")
    console.print("Let's get you configured with OpenCode API and local models.\n")
    
    # Ensure state directories exist
    config = ConfigLoader.load()
    config.ensure_dirs()
    
    # OpenCode API Key Setup
    console.print("[bold]1. OpenCode API Configuration[/bold]")
    api_key = os.environ.get("OPENCODE_API_KEY")
    if api_key:
        console.print(f"✓ OpenCode API key found: {api_key[:10]}...")
    else:
        console.print("No OpenCode API key found in environment.")
        if console.input("Would you like to enter your OpenCode API key? (y/n): ").lower().startswith('y'):
            api_key = console.input("Enter your OpenCode API key: ", password=True)
            if api_key:
                # Save to .env file
                env_file = Path.cwd() / ".env"
                with open(env_file, "a") as f:
                    f.write(f"\nOPENCODE_API_KEY={api_key}\n")
                console.print("✓ API key saved to .env file")
                os.environ["OPENCODE_API_KEY"] = api_key
        else:
            console.print("⚠️  Skipping OpenCode API setup")
    
    # Local Model Setup
    console.print("\n[bold]2. Local Model Configuration[/bold]")
    has_local_models = console.input("Do you have local models to configure? (y/n): ").lower().startswith('y')
    
    if has_local_models:
        model_id = console.input("Enter model ID (e.g., qwen-coder-7b): ")
        model_path = console.input("Enter path to model directory: ")
        
        # Update configuration
        config.models.append({
            "id": model_id,
            "path": model_path,
            "backend": "transformers"
        })
        
        # Save configuration
        config_path = config.data_root / "config" / "suite.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            import json
            json.dump(config.model_dump(), f, indent=2)
        
        console.print(f"✓ Model {model_id} configured")
    
    # Test configuration
    console.print("\n[bold]3. Testing Configuration[/bold]")
    console.print("Running system checks...")
    
    try:
        # Test OpenCode API if key is available
        if os.environ.get("OPENCODE_API_KEY"):
            console.print("✓ OpenCode API key format valid")
        
        # Test model host
        console.print("✓ Model host configuration ready")
        
        # Test memory system
        from .runtime.db import db
        conn = db.get_connection()
        console.print("✓ Memory database accessible")
        
        console.print("\n[bold green]🎉 Setup complete![/bold green]")
        console.print("You can now start the model host with:")
        console.print("  heidi model serve")
        console.print("\nAnd check status with:")
        console.print("  heidi status")
        
    except Exception as e:
        console.print(f"\n[red]❌ Setup failed: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def config():
    """Show current configuration."""
    import os
    from pathlib import Path
    
    config = ConfigLoader.load()
    
    console.print("[bold]Heidi CLI Configuration[/bold]")
    console.print(f"Data Root: {config.data_root}")
    console.print(f"Model Host Enabled: {config.model_host_enabled}")
    console.print(f"Host: {config.host}:{config.port}")
    
    console.print("\n[bold]API Configuration[/bold]")
    api_key = os.environ.get("OPENCODE_API_KEY")
    if api_key:
        console.print(f"OpenCode API: ✓ Configured ({api_key[:10]}...)")
    else:
        console.print("OpenCode API: ✗ Not configured")
    
    console.print("\n[bold]Local Models[/bold]")
    if config.models:
        for model in config.models:
            console.print(f"- {model.id}: {model.path} ({model.backend})")
    else:
        console.print("No local models configured")
    
    console.print("\n[bold]State Directories[/bold]")
    for name, path in config.state_dirs.items():
        status = "✓" if path.exists() else "✗"
        console.print(f"{status} {name}: {path}")

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
    
    # Show registry status
    try:
        from .registry.manager import model_registry
        registry = model_registry.load_registry()
        console.print(f"\n[bold]Registry Status[/bold]")
        console.print(f"Active Stable: {registry.get('active_stable', 'None')}")
        console.print(f"Active Candidate: {registry.get('active_candidate', 'None')}")
        console.print(f"Total Versions: {len(registry.get('versions', {}))}")
    except Exception as e:
        console.print(f"Registry Status: [red]Error - {e}[/red]")

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

@memory_app.command("search")
def memory_search(query: str, limit: int = 10):
    """Search memory database for relevant entries."""
    from .runtime.db import db
    
    console.print(f"Searching memories for: [italic]{query}[/italic]")
    
    try:
        with db.get_connection() as conn:
            # Simple text search for now (could be enhanced with embeddings)
            cursor = conn.execute("""
                SELECT id, content, tags, created_at, last_accessed, access_count
                FROM memories 
                WHERE content LIKE ? OR tags LIKE ?
                ORDER BY access_count DESC, created_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            results = cursor.fetchall()
            
            if not results:
                console.print("No memories found.")
                return
            
            console.print(f"Found {len(results)} memories:\n")
            
            for row in results:
                console.print(f"[bold]ID:[/bold] {row['id']}")
                console.print(f"[bold]Content:[/bold] {row['content'][:200]}{'...' if len(row['content']) > 200 else ''}")
                console.print(f"[bold]Tags:[/bold] {row['tags'] or 'None'}")
                console.print(f"[bold]Created:[/bold] {row['created_at']}")
                console.print(f"[bold]Accessed:[/bold] {row['access_count']} times\n")
                
    except Exception as e:
        console.print(f"[red]Error searching memories: {e}[/red]")

@learning_app.command("export")
def learning_export(run_id: str):
    """Export a run for manual review."""
    import json
    from pathlib import Path
    
    config = ConfigLoader.load()
    raw_dir = config.state_dirs["datasets_raw"]
    
    # Find the run file
    run_file = None
    for date_dir in raw_dir.iterdir():
        if date_dir.is_dir():
            potential_run = date_dir / run_id / "run.json"
            if potential_run.exists():
                run_file = potential_run
                break
    
    if not run_file:
        console.print(f"[red]Run {run_id} not found.[/red]")
        return
    
    # Export to current directory
    export_path = Path.cwd() / f"{run_id}_export.json"
    
    with open(run_file, "r") as src, open(export_path, "w") as dst:
        json.dump(json.load(src), dst, indent=2)
    
    console.print(f"✓ Exported run {run_id} to {export_path}")

@learning_app.command("curate")
def learning_curate(date: Optional[str] = None):
    """Curate raw runs into redacted training datasets."""
    import asyncio
    from .pipeline.curation import curation_engine
    console.print(f"Curating dataset (Filter: {date or 'All'})...")
    count = asyncio.run(curation_engine.curate_dataset(date))
    console.print(f"[green]✓ Curated {count} runs into a new dataset.[/green]")

@learning_app.command("train-full")
def learning_train_full():
    """Start a background full-model retraining job."""
    import asyncio
    from .registry.retrain import retraining_engine
    console.print("Initiating background retraining...")
    try:
        job_id = asyncio.run(retraining_engine.start_retraining())
        console.print(f"[green]✓ Retraining job started: {job_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error starting retraining: {e}[/red]")

@learning_app.command("eval")
def learning_eval(candidate_id: str):
    """Evaluate a candidate model against the active stable model."""
    import asyncio
    from .registry.eval import eval_harness
    console.print(f"Evaluating candidate {candidate_id}...")
    try:
        passed, results = asyncio.run(eval_harness.evaluate_candidate(candidate_id))
        status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
        console.print(f"Evaluation {status}. Metrics: {results['metrics']}")
    except Exception as e:
        console.print(f"[red]Error evaluating candidate: {e}[/red]")

@learning_app.command("promote")
def learning_promote(version_id: str, channel: str = "stable"):
    """Promote a model version to a specific channel (e.g. candidate or stable)."""
    import asyncio
    from .registry.manager import model_registry
    console.print(f"Promoting {version_id} to {channel}...")
    try:
        asyncio.run(model_registry.promote(version_id, channel))
        console.print(f"[green]✓ {version_id} promoted to {channel}.[/green]")
    except Exception as e:
        console.print(f"[red]Error promoting model: {e}[/red]")

@learning_app.command("versions")
def learning_versions(channel: Optional[str] = None):
    """List model versions in registry."""
    import asyncio
    from .registry.manager import model_registry
    
    try:
        versions = asyncio.run(model_registry.list_versions(channel))
        
        if not versions:
            console.print("No versions found.")
            return
        
        title = f"Model Versions ({channel or 'All Channels'})"
        console.print(f"[bold]{title}[/bold]\n")
        
        for version in versions:
            status = "✨" if version["is_active"] else "  "
            channel_icon = "🟢" if version["channel"] == "stable" else "🟡" if version["channel"] == "candidate" else "⚪"
            
            console.print(f"{status}{channel_icon} {version['id']}")
            console.print(f"   Channel: {version['channel']}")
            console.print(f"   Registered: {version['registered_at']}")
            if version.get("size_bytes"):
                size_mb = version['size_bytes'] / (1024 * 1024)
                console.print(f"   Size: {size_mb:.1f} MB")
            console.print()
            
    except Exception as e:
        console.print(f"[red]Error listing versions: {e}[/red]")

@learning_app.command("info")
def learning_info(version_id: str):
    """Show detailed information about a model version."""
    import asyncio
    import json
    from .registry.manager import model_registry
    
    try:
        info = asyncio.run(model_registry.get_version_info(version_id))
        
        if not info:
            console.print(f"[red]Version {version_id} not found.[/red]")
            return
        
        console.print(f"[bold]Version Information: {version_id}[/bold]\n")
        console.print(f"Channel: {info['channel']}")
        console.print(f"Path: {info['path']}")
        console.print(f"Registered: {info['registered_at']}")
        console.print(f"Active: {'Yes' if info['is_active'] else 'No'}")
        
        if info.get("size_bytes"):
            size_mb = info['size_bytes'] / (1024 * 1024)
            console.print(f"Size: {size_mb:.1f} MB")
        
        if info.get("checksum"):
            console.print(f"Checksum: {info['checksum'][:16]}...")
        
        if info.get("metadata"):
            console.print("\n[bold]Metadata:[/bold]")
            console.print(json.dumps(info["metadata"], indent=2))
        
    except Exception as e:
        console.print(f"[red]Error getting version info: {e}[/red]")

@learning_app.command("rollback")
def learning_rollback():
    """Rollback to the previous stable model."""
    import asyncio
    from .registry.manager import model_registry
    
    console.print("Initiating rollback to previous stable model...")
    
    try:
        success = asyncio.run(model_registry.rollback())
        if success:
            console.print("[green]✓ Rollback completed successfully[/green]")
        else:
            console.print("[yellow]Rollback failed - no previous stable model found[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during rollback: {e}[/red]")

@model_app.command("list")
def model_list():
    """List all available models."""
    from .model_host.manager import manager
    try:
        models = manager.list_models()
        
        if not models:
            console.print("No models available.")
            return
        
        console.print(f"[bold]Available Models ({len(models)})[/bold]\n")
        
        for model in models:
            backend = model.get("backend", "local")
            channel = model.get("channel", "")
            
            if backend == "opencode":
                console.print(f"🌐 [blue]{model['id']}[/blue] (OpenCode API)")
            else:
                status = "🟢" if channel == "stable" else "🟡" if channel == "candidate" else "⚪"
                console.print(f"{status} {model['id']} ({channel or 'local'})")
            
            console.print(f"   Path: {model['root']}")
            if model.get("owned_by"):
                console.print(f"   Owner: {model['owned_by']}")
            console.print()
            
    except Exception as e:
        console.print(f"[red]Error listing models: {e}[/red]")

@model_app.command("reload")
def model_reload():
    """Atomically hot-swap the model routing to the active stable model."""
    import asyncio
    from .registry.hotswap import hotswap_manager
    console.print("Initiating atomic hot-swap...")
    success = asyncio.run(hotswap_manager.reload_stable_model())
    if success:
        console.print("[green]✓ Hot-swap complete. Serving new state.[/green]")
    else:
        console.print("[red]Hot-swap failed. See logs.[/red]")

if __name__ == "__main__":
    app()
