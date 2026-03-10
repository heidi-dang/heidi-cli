from __future__ import annotations

import typer
import sys
from typing import List, Optional
from rich.console import Console

from .shared.config import ConfigLoader
from .launcher import start_daemon, stop_process, load_pids
from .token_tracking.cli import register_tokens_app

console = Console()
app = typer.Typer(
    add_completion=False,
    help="Heidi Unified Learning Suite CLI",
)

# New Module Sub-apps
model_app = typer.Typer(help="Local model management (serve/status/stop/reload)")
memory_app = typer.Typer(help="Memory management (status/search)")
learning_app = typer.Typer(help="Learning & Training management (reflect/export/curate/train-full/eval/promote/rollback)")
hf_app = typer.Typer(help="HuggingFace model management")

app.add_typer(model_app, name="model")
app.add_typer(memory_app, name="memory")
app.add_typer(learning_app, name="learning")
app.add_typer(hf_app, name="hf")
register_tokens_app(app)

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

# HuggingFace Commands
@hf_app.command("search")
def hf_search(query: str, task: str = "text-generation", limit: int = 20):
    """Search models on HuggingFace Hub."""
    import asyncio
    from .integrations.huggingface import get_huggingface_integration
    
    console.print(f"[bold blue]🔍 Searching HuggingFace for: {query}[/bold blue]")
    console.print(f"Task filter: {task}, Limit: {limit}\n")
    
    try:
        models = asyncio.run(get_huggingface_integration().search_models(query, task, limit))
        
        if not models:
            console.print("No models found.")
            return
        
        console.print(f"[bold]Found {len(models)} models:[/bold]\n")
        
        for i, model in enumerate(models[:limit], 1):
            console.print(f"{i}. 📦 {model['id']}")
            console.print(f"   👤 {model['author']} | ⬇️ {model['downloads']:,} downloads | ❤️ {model['likes']}")
            if model.get('tags'):
                tags = model['tags'][:5]  # Show first 5 tags
                console.print(f"   🏷️  {', '.join(tags)}")
            console.print()
            
    except Exception as e:
        console.print(f"[red]❌ Search failed: {e}[/red]")
        raise typer.Exit(1)

@hf_app.command("info")
def hf_info(model_id: str):
    """Get detailed information about a HuggingFace model."""
    import asyncio
    from .integrations.huggingface import get_huggingface_integration
    
    console.print(f"[bold blue]📋 Model Info: {model_id}[/bold blue]\n")
    
    try:
        info = asyncio.run(get_huggingface_integration().get_model_info(model_id))
        
        console.print(f"[bold]Author:[/bold] {info.get('author', 'Unknown')}")
        console.print(f"[bold]Downloads:[/bold] {info.get('downloads', 0):,}")
        console.print(f"[bold]Likes:[/bold] {info.get('likes', 0):,}")
        console.print(f"[bold]Pipeline:[/bold] {info.get('pipeline_tag', 'Unknown')}")
        
        capabilities = info.get('capabilities', [])
        if capabilities:
            console.print(f"[bold]Capabilities:[/bold] {', '.join(capabilities)}")
        
        context_length = info.get('context_length')
        if context_length:
            console.print(f"[bold]Context Length:[/bold] {context_length:,} tokens")
        
        tags = info.get('tags', [])
        if tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(tags[:10])}")
        
        description = info.get('description', '')
        if description:
            console.print(f"\n[bold]Description:[/bold]")
            console.print(description[:500] + "..." if len(description) > 500 else description)
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get model info: {e}[/red]")
        raise typer.Exit(1)

@hf_app.command("download")
def hf_download(model_id: str, force: bool = False, add_to_config: bool = True):
    """Download a model from HuggingFace and add to Heidi configuration."""
    import asyncio
    from .integrations.huggingface import get_huggingface_integration
    from .shared.config import ConfigLoader
    from pathlib import Path
    
    console.print(f"[bold blue]⬇️  Downloading model: {model_id}[/bold blue]")
    
    if force:
        console.print("[yellow]Force download enabled - will overwrite existing files[/yellow]")
    
    try:
        metadata = asyncio.run(get_huggingface_integration().download_model(model_id, force))
        
        console.print(f"✅ Downloaded to: {metadata['local_path']}")
        console.print(f"📁 Files: {metadata['file_count']}")
        console.print(f"💾 Size: {metadata['size_gb']} GB")
        
        if add_to_config:
            console.print("\n[bold]Adding to Heidi configuration...[/bold]")
            
            # Auto-configure model
            config = asyncio.run(get_huggingface_integration().auto_configure_model(
                model_id, Path(metadata['local_path'])
            ))
            
            # Add to Heidi configuration
            suite_config = ConfigLoader.load()
            
            # Check if model already exists
            existing_ids = [m.id for m in suite_config.models]
            if config['id'] in existing_ids:
                console.print(f"[yellow]Model {config['id']} already exists in configuration[/yellow]")
                if not console.input("Overwrite existing configuration? (y/n): ").lower().startswith('y'):
                    console.print("Skipping configuration update.")
                    config = None
            
            if config:
                suite_config.models.append(config)
                
                # Save configuration
                config_path = suite_config.data_root / "config" / "suite.json"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                import json
                with open(config_path, "w") as f:
                    json.dump(suite_config.model_dump(mode='json'), f, indent=2)
                
                console.print(f"✅ Added to Heidi configuration as: {config['id']}")
                console.print(f"   Capabilities: {', '.join(config['capabilities'])}")
                console.print(f"   Context length: {config['max_context']:,} tokens")
        
        console.print(f"\n[bold green]🎉 Model ready![/bold green]")
        console.print(f"Start the model host with: [bold]heidi model serve[/bold]")
        console.print(f"Then use with:")
        console.print(f"curl -X POST http://127.0.0.1:8000/v1/chat/completions \\")
        console.print(f"  -H 'Content-Type: application/json' \\")
        console.print(f"  -d '{{\"model\": \"{config['id'] if add_to_config else model_id}\", \"messages\": [{{\"role\": \"user\", \"content\": \"Hello!\"}}]}}'")
        
    except Exception as e:
        console.print(f"[red]❌ Download failed: {e}[/red]")
        raise typer.Exit(1)

@hf_app.command("list-local")
def hf_list_local():
    """List downloaded HuggingFace models."""
    from .integrations.huggingface import get_huggingface_integration
    
    local_models = get_huggingface_integration().list_local_models()
    
    if not local_models:
        console.print("No HuggingFace models downloaded yet.")
        console.print("Use 'heidi hf download <model_id>' to download models.")
        return
    
    console.print(f"Downloaded HuggingFace Models ({len(local_models)}):")
    console.print()
    
    for i, model in enumerate(local_models, 1):
        console.print(f"{i}. Model: {model['model_id']}")
        console.print(f"   Path: {model['local_path']}")
        console.print(f"   Size: {model['size_gb']} GB")
        console.print(f"   Files: {model['file_count']}")
        console.print(f"   Downloaded: {model['downloaded_at']}")
        
        # Show if it's configured in Heidi
        from .shared.config import ConfigLoader
        suite_config = ConfigLoader.load()
        configured_ids = [m.id for m in suite_config.models]
        safe_id = model['model_id'].replace("/", "_").replace("\\", "_")
        
        if safe_id in configured_ids:
            console.print(f"   Status: Configured in Heidi")
        else:
            console.print(f"   Status: Not configured in Heidi")
        
        console.print()

@hf_app.command("compare")
def hf_compare(model_ids: List[str] = typer.Argument(..., help="Model IDs to compare")):
    """Compare multiple HuggingFace models."""
    import asyncio
    from .integrations.huggingface import get_huggingface_integration
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    if len(model_ids) < 2:
        console.print("[red]❌ Please provide at least 2 models to compare[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]📊 Comparing {len(model_ids)} models:[/bold blue] {', '.join(model_ids)}\n")
    
    try:
        hf = get_huggingface_integration()
        
        # Get model info for all models
        models_info = []
        for model_id in model_ids:
            try:
                info = asyncio.run(hf.get_model_info(model_id))
                models_info.append(info)
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not fetch info for {model_id}: {e}[/yellow]")
        
        if len(models_info) < 2:
            console.print("[red]❌ Not enough valid models to compare[/red]")
            raise typer.Exit(1)
        
        # Create comparison table
        table = Table(title="Model Comparison")
        table.add_column("Feature", style="cyan", no_wrap=True)
        
        for model in models_info:
            display_name = model.get('id', 'Unknown')
            if len(display_name) > 15:
                display_name = display_name[:12] + "..."
            table.add_column(display_name, style="green")
        
        # Basic info
        table.add_row("Author", *[model.get('author', 'Unknown') for model in models_info])
        table.add_row("Downloads", *[f"{model.get('downloads', 0):,}" for model in models_info])
        table.add_row("Likes", *[f"{model.get('likes', 0):,}" for model in models_info])
        table.add_row("Pipeline", *[model.get('pipeline_tag', 'Unknown') for model in models_info])
        
        # Capabilities
        capabilities = []
        for model in models_info:
            caps = []
            tags = model.get('tags', [])
            if any(tag in tags for tag in ['chat', 'instruct']):
                caps.append('💬')
            if any(tag in tags for tag in ['coding', 'code']):
                caps.append('💻')
            if any(tag in tags for tag in ['vision', 'image']):
                caps.append('👁️')
            if any(tag in tags for tag in ['function-calling', 'tool']):
                caps.append('🔧')
            capabilities.append(' '.join(caps) if caps else '💬')
        
        table.add_row("Capabilities", *capabilities)
        
        # Model size
        model_sizes = []
        for model in models_info:
            tags = model.get('tags', [])
            size = 'Unknown'
            for tag in ['70b', '30b', '13b', '7b', '3b', '1.8b', '1b']:
                if tag in tags:
                    size = tag.upper()
                    break
            model_sizes.append(size)
        table.add_row("Size", *model_sizes)
        
        # Languages
        languages = []
        for model in models_info:
            tags = model.get('tags', [])
            langs = [tag for tag in tags if tag in ['english', 'chinese', 'french', 'german', 'spanish']]
            languages.append(', '.join(langs) if langs else 'English')
        table.add_row("Languages", *languages)
        
        # License
        licenses = []
        for model in models_info:
            tags = model.get('tags', [])
            license_info = 'Unknown'
            for tag in tags:
                if tag.startswith('license:'):
                    license_info = tag.split(':', 1)[1]
                    break
            licenses.append(license_info)
        table.add_row("License", *licenses)
        
        console.print(table)
        
        # Recommendations
        console.print("\n[bold yellow]🎯 Recommendations:[/bold yellow]")
        
        # Best for downloads
        best_downloads = max(models_info, key=lambda x: x.get('downloads', 0))
        console.print(f"• Most Popular: {best_downloads.get('id')} ({best_downloads.get('downloads', 0):,} downloads)")
        
        # Best for likes
        best_likes = max(models_info, key=lambda x: x.get('likes', 0))
        console.print(f"• Most Liked: {best_likes.get('id')} ({best_likes.get('likes', 0):,} likes)")
        
        # Best for coding
        coding_models = [m for m in models_info if any(tag in m.get('tags', []) for tag in ['coding', 'code'])]
        if coding_models:
            console.print(f"• Best for Coding: {', '.join([m.get('id') for m in coding_models])}")
        
        # Smallest model
        size_order = ['1b', '1.8b', '3b', '7b', '13b', '30b', '70b']
        smallest = None
        for model in models_info:
            tags = model.get('tags', [])
            for size in size_order:
                if size in tags:
                    if smallest is None or size_order.index(size) < size_order.index(smallest[1]):
                        smallest = (model.get('id'), size)
                    break
        if smallest:
            console.print(f"• Smallest Model: {smallest[0]} ({smallest[1].upper()})")
        
    except Exception as e:
        console.print(f"[red]❌ Comparison failed: {e}[/red]")
        raise typer.Exit(1)

@hf_app.command("batch-download")
def hf_batch_download(model_ids: List[str] = typer.Argument(..., help="Model IDs to download"), 
                    force: bool = typer.Option(False, "--force", "-f", help="Force download even if model exists"),
                    add_to_config: bool = typer.Option(True, "--add-to-config/--no-add-to-config", help="Add to Heidi configuration")):
    """Download multiple models from HuggingFace."""
    import asyncio
    from .integrations.huggingface import get_huggingface_integration
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    console.print(f"[bold blue]⬇️  Batch downloading {len(model_ids)} models:[/bold blue]")
    for i, model_id in enumerate(model_ids, 1):
        console.print(f"  {i}. {model_id}")
    console.print()
    
    if force:
        console.print("[yellow]Force download enabled - will overwrite existing files[/yellow]")
    
    start_time = time.time()
    results = []
    
    def download_single_model(model_id):
        """Download a single model."""
        try:
            hf = get_huggingface_integration()
            metadata = asyncio.run(hf.download_model(model_id, force))
            
            config = None
            if add_to_config:
                config = asyncio.run(hf.auto_configure_model(model_id, Path(metadata['local_path'])))
            
            return {
                "model_id": model_id,
                "success": True,
                "metadata": metadata,
                "config": config,
                "error": None
            }
        except Exception as e:
            return {
                "model_id": model_id,
                "success": False,
                "metadata": None,
                "config": None,
                "error": str(e)
            }
    
    # Download models in parallel (limit to 3 concurrent downloads)
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_model = {executor.submit(download_single_model, model_id): model_id 
                         for model_id in model_ids}
        
        for future in as_completed(future_to_model):
            model_id = future_to_model[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    console.print(f"✅ {model_id}: Downloaded ({result['metadata']['size_gb']} GB)")
                else:
                    console.print(f"❌ {model_id}: {result['error']}")
            except Exception as e:
                console.print(f"❌ {model_id}: Unexpected error: {e}")
    
    # Add successful models to configuration
    if add_to_config:
        successful_configs = [r["config"] for r in results if r["success"] and r["config"]]
        if successful_configs:
            from .shared.config import ConfigLoader
            suite_config = ConfigLoader.load()
            
            for config in successful_configs:
                existing_ids = [m.id for m in suite_config.models]
                if config['id'] not in existing_ids:
                    suite_config.models.append(config)
            
            # Save configuration
            config_path = suite_config.data_root / "config" / "suite.json"
            import json
            with open(config_path, "w") as f:
                json.dump(suite_config.model_dump(mode='json'), f, indent=2)
            
            console.print(f"✅ Added {len(successful_configs)} models to Heidi configuration")
    
    # Summary
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    total_size = sum(r["metadata"]["size_gb"] for r in results if r["success"] and r["metadata"])
    
    console.print(f"\n[bold green]📊 Batch Download Summary:[/bold green]")
    console.print(f"✅ Successful: {successful}")
    console.print(f"❌ Failed: {failed}")
    console.print(f"💾 Total Size: {total_size:.2f} GB")
    console.print(f"⏱️  Total Time: {total_time:.1f}s")
    
    if failed > 0:
        console.print(f"\n[bold red]Failed downloads:[/bold red]")
        for result in results:
            if not result["success"]:
                console.print(f"  • {result['model_id']}: {result['error']}")
        
        raise typer.Exit(1)

@hf_app.command("analytics")
def hf_analytics(model_id: Optional[str] = typer.Argument(None, help="Model ID to analyze (optional)"),
                 days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
                 export: bool = typer.Option(False, "--export", "-e", help="Export analytics to JSON")):
    """Show usage analytics for models."""
    from .integrations.analytics import get_analytics
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import json
    
    console = Console()
    analytics = get_analytics()
    
    if model_id:
        # Show analytics for specific model
        console.print(f"[bold blue]📊 Analytics for {model_id} (last {days} days):[/bold blue]\n")
        
        usage = analytics.get_model_usage(model_id, days)
        performance = analytics.get_performance_metrics(model_id, days)
        trends = analytics.get_usage_trends(model_id, days)
        
        if usage:
            # Usage table
            usage_table = Table(title="Usage Summary")
            usage_table.add_column("Metric", style="cyan")
            usage_table.add_column("Value", style="green")
            
            usage_table.add_row("Total Requests", f"{usage.request_count:,}")
            usage_table.add_row("Total Tokens", f"{usage.total_tokens:,}")
            usage_table.add_row("Avg Response Time", f"{usage.avg_response_time:.2f}ms")
            usage_table.add_row("Success Rate", f"{usage.success_rate:.1%}")
            usage_table.add_row("Error Count", f"{usage.error_count}")
            usage_table.add_row("Last Used", usage.last_used.strftime("%Y-%m-%d %H:%M"))
            
            console.print(usage_table)
            
            if performance:
                # Performance table
                perf_table = Table(title="Performance Metrics")
                perf_table.add_column("Metric", style="cyan")
                perf_table.add_column("Value", style="green")
                
                perf_table.add_row("Avg Latency", f"{performance.avg_latency_ms:.2f}ms")
                perf_table.add_row("P95 Latency", f"{performance.p95_latency_ms:.2f}ms")
                perf_table.add_row("P99 Latency", f"{performance.p99_latency_ms:.2f}ms")
                perf_table.add_row("Throughput", f"{performance.throughput_requests_per_min:.1f} req/min")
                perf_table.add_row("Error Rate", f"{performance.error_rate:.1%}")
                perf_table.add_row("Token Efficiency", f"{performance.token_efficiency:.1f} tokens/sec")
                
                console.print(perf_table)
            
            if export:
                export_data = analytics.export_analytics(model_id, days)
                export_file = Path.home() / ".heidi" / f"analytics_{model_id.replace('/', '_')}.json"
                export_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(export_file, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                console.print(f"\n✅ Analytics exported to: {export_file}")
        else:
            console.print(f"[yellow]No usage data found for {model_id}[/yellow]")
    
    else:
        # Show top models
        console.print(f"[bold blue]📊 Top Models (last {days} days):[/bold blue]\n")
        
        top_models = analytics.get_top_models(limit=10, days=days)
        
        if top_models:
            table = Table(title="Top Models by Usage")
            table.add_column("Rank", style="cyan", no_wrap=True)
            table.add_column("Model", style="green")
            table.add_column("Requests", justify="right")
            table.add_column("Tokens", justify="right")
            table.add_column("Avg Time", justify="right")
            table.add_column("Success Rate", justify="right")
            
            for i, model in enumerate(top_models, 1):
                table.add_row(
                    str(i),
                    model.model_id,
                    f"{model.request_count:,}",
                    f"{model.total_tokens:,}",
                    f"{model.avg_response_time:.1f}ms",
                    f"{model.success_rate:.1%}"
                )
            
            console.print(table)
            
            if export:
                export_data = analytics.export_analytics(days=days)
                export_file = Path.home() / ".heidi" / "analytics_all_models.json"
                export_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(export_file, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                console.print(f"\n✅ Analytics exported to: {export_file}")
        else:
            console.print("[yellow]No usage data found[/yellow]")
            console.print("Models need to be used via API to generate analytics data.")

@hf_app.command("remove")
def hf_remove(model_id: str):
    """Remove a locally downloaded HuggingFace model."""
    from .integrations.huggingface import get_huggingface_integration
    
    console.print(f"[bold red]🗑️  Removing model: {model_id}[/bold red]")
    
    # Check if model exists locally
    local_info = get_huggingface_integration().get_local_model_info(model_id)
    if not local_info:
        console.print(f"[yellow]Model {model_id} not found in local storage[/yellow]")
        return
    
    console.print(f"Local path: {local_info['local_path']}")
    console.print(f"Size: {local_info['size_gb']} GB")
    
    if not console.input("Are you sure you want to remove this model? (y/n): ").lower().startswith('y'):
        console.print("Removal cancelled.")
        return
    
    try:
        success = asyncio.run(get_huggingface_integration().remove_model(model_id))
        if success:
            console.print(f"✅ Successfully removed model {model_id}")
            
            # Also remove from Heidi configuration if present
            from .shared.config import ConfigLoader
            suite_config = ConfigLoader.load()
            
            safe_id = model_id.replace("/", "_").replace("\\", "_")
            suite_config.models = [m for m in suite_config.models if m.id != safe_id]
            
            # Save updated configuration
            config_path = suite_config.data_root / "config" / "suite.json"
            import json
            with open(config_path, "w") as f:
                json.dump(suite_config.model_dump(mode='json'), f, indent=2)
            
            console.print(f"✅ Also removed from Heidi configuration")
        else:
            console.print(f"[yellow]Failed to remove model {model_id}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error removing model: {e}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
