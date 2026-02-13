from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import ConfigManager
from .logging import HeidiLogger, setup_global_logging
from .orchestrator.loop import run_loop, pick_executor as _pick_executor
from .orchestrator.registry import AgentRegistry
from .openwebui_commands import openwebui_app

app = typer.Typer(add_completion=False, help="Heidi CLI - Copilot/Jules/OpenCode orchestrator")
copilot_app = typer.Typer(help="Copilot (Copilot CLI via GitHub Copilot SDK)")
auth_app = typer.Typer(help="Authentication commands")
agents_app = typer.Typer(help="Agent management")
valves_app = typer.Typer(help="Configuration valves")
persona_app = typer.Typer(help="Persona management")

app.add_typer(copilot_app, name="copilot")
app.add_typer(auth_app, name="auth")
app.add_typer(agents_app, name="agents")
app.add_typer(valves_app, name="valves")
app.add_typer(openwebui_app, name="openwebui")
app.add_typer(persona_app, name="persona")

console = Console()
json_output = False
verbose_mode = False


def get_version() -> str:
    from . import __version__
    return __version__


def print_json(data: Any) -> None:
    if json_output:
        print(json.dumps(data, indent=2))


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version"),
    json: bool = typer.Option(False, "--json", help="Output JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    global json_output, verbose_mode
    json_output = json
    verbose_mode = verbose
    if verbose:
        setup_global_logging("DEBUG")
    if version:
        console.print(f"Heidi CLI v{get_version()}")
        raise typer.Exit(0)

    # Check if Heidi is initialized - if not, automatically start wizard
    # Skip wizard if CI=true or HEIDI_NO_WIZARD=1
    import os
    if not ConfigManager.config_file().exists() and not os.environ.get("HEIDI_NO_WIZARD"):
        console.print(Panel.fit(
            "[yellow]Heidi CLI is not initialized yet.[/yellow]\n\n"
            "Starting setup wizard...",
            title="First Time Setup"
        ))
        from .setup_wizard import SetupWizard
        wizard = SetupWizard()
        wizard.run()
        raise typer.Exit(0)


@app.command()
def setup() -> None:
    """Run the interactive setup wizard."""
    from .setup_wizard import SetupWizard
    
    wizard = SetupWizard()
    wizard.run()


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Initialize Heidi CLI configuration directory."""
    ConfigManager.ensure_dirs()

    if ConfigManager.config_file().exists() and not force:
        console.print("[yellow]Heidi already initialized. Use --force to reinitialize.[/yellow]")
        return

    config = ConfigManager.load_config()
    ConfigManager.save_config(config)
    console.print(f"[green]Initialized Heidi at {ConfigManager.heidi_dir()}[/green]")
    console.print(f"  Config: {ConfigManager.config_file()}")
    console.print(f"  Secrets: {ConfigManager.secrets_file()}")
    console.print(f"  Runs: {ConfigManager.runs_dir()}")
    console.print(f"  Tasks: {ConfigManager.TASKS_DIR}")


@app.command()
def doctor() -> None:
    """Check health of all executors and dependencies."""
    import sys
    from .config import ConfigManager

    table = Table(title="Heidi CLI Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version/Notes", style="white")

    checks = []
    has_failures = False

    result = shutil.which("python3") or shutil.which("python")
    if result:
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if sys.version_info >= (3, 10):
            checks.append(("Python", "ok", version))
        else:
            checks.append(("Python", "fail", f"{version} (need 3.10+)"))
            has_failures = True
    else:
        checks.append(("Python", "fail", "not found"))
        has_failures = True

    import importlib.util
    if importlib.util.find_spec("copilot"):
        checks.append(("Copilot SDK", "ok", "installed"))
    else:
        checks.append(("Copilot SDK", "missing", "pip install github-copilot-sdk"))

    result = shutil.which("opencode")
    checks.append(("OpenCode", "ok" if result else "not found", result or ""))

    result = shutil.which("jules")
    checks.append(("Jules CLI", "ok" if result else "not found", result or ""))

    result = shutil.which("code")
    checks.append(("VS Code", "ok" if result else "not found", result or ""))

    heidi_dir = ConfigManager.heidi_dir()
    tasks_dir = ConfigManager.TASKS_DIR
    if heidi_dir.exists():
        checks.append((".heidi/ dir", "ok", str(heidi_dir)))
    else:
        checks.append((".heidi/ dir", "warning", "not initialized (run heidi init)"))

    if tasks_dir.exists():
        checks.append(("./tasks/ dir", "ok", str(tasks_dir)))
    else:
        checks.append(("./tasks/ dir", "warning", "not created yet"))

    config = ConfigManager.load_config()
    checks.append(("Telemetry", "enabled" if config.telemetry_enabled else "disabled", f"telemetry_enabled={config.telemetry_enabled}"))
    checks.append(("Provider", "ok", config.provider or "copilot"))
    checks.append(("Server URL", "ok", config.server_url))

    if config.openwebui_url:
        checks.append(("OpenWebUI", "ok", config.openwebui_url))
    else:
        checks.append(("OpenWebUI", "not set", "optional"))

    token = ConfigManager.get_github_token()
    if token:
        checks.append(("GitHub Auth", "ok", "token configured"))
    else:
        checks.append(("GitHub Auth", "not configured", "optional for local provider"))

    for name, status, notes in checks:
        if status == "fail":
            style = "red"
            has_failures = True
        elif status == "warning":
            style = "yellow"
        elif status == "ok" or status == "enabled":
            style = "green"
        else:
            style = "white"
        table.add_row(name, f"[{style}]{status}[/{style}]", notes)

    console.print(table)

    if has_failures:
        console.print("[red]Fatal issues found. Run 'heidi init' first.[/red]")
        raise typer.Exit(1)

    missing = [n for n, s, _ in checks if s in ("missing", "not configured")]
    if missing:
        console.print(f"[yellow]Warning: Missing components: {', '.join(missing)}[/yellow]")


@auth_app.command("gh")
def auth_gh(
    token: Optional[str] = typer.Option(None, help="GitHub token (or prompt if not provided)"),
    store_keyring: bool = typer.Option(True, help="Store in OS keyring"),
) -> None:
    """Authenticate with GitHub for Copilot access."""
    if not token:
        token = typer.prompt("Enter GitHub token (with copilot scope)", hide_input=True)

    if not token:
        console.print("[red]Token required[/red]")
        raise typer.Exit(1)

    ConfigManager.set_github_token(token, store_keyring=store_keyring)
    console.print("[green]GitHub token stored successfully[/green]")

    if store_keyring:
        console.print("[dim]Token also stored in OS keyring[/dim]")
    else:
        console.print("[dim]Token stored only in secrets file[/dim]")


@auth_app.command("status")
def auth_status() -> None:
    """Show authentication status."""
    token = ConfigManager.get_github_token()
    if token:
        console.print("[green]GitHub token: configured[/green]")
    else:
        console.print("[yellow]GitHub token: not configured[/yellow]")


@copilot_app.command("doctor")
def copilot_doctor() -> None:
    """Check Copilot SDK health and auth status."""
    from .copilot_runtime import CopilotRuntime

    async def _run():
        rt = CopilotRuntime()
        await rt.start()
        try:
            table = Table(title="Copilot SDK Status")
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="green")

            try:
                st = await rt.client.get_status()
                table.add_row("CLI State", "connected")
                table.add_row("CLI Version", str(getattr(st, 'cliVersion', 'unknown')))
            except Exception:
                table.add_row("CLI State", "error")

            try:
                auth = await rt.client.get_auth_status()
                table.add_row("Authenticated", str(getattr(auth, 'isAuthenticated', False)))
                table.add_row("Login", str(getattr(auth, 'login', 'unknown')))
            except Exception:
                table.add_row("Authenticated", "unknown")
                table.add_row("Login", "unknown")

            console.print(table)
        except Exception as e:
            console.print(f"[red]Doctor check failed: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await rt.stop()

    asyncio.run(_run())


@copilot_app.command("status")
def copilot_status() -> None:
    """Print auth + health status from Copilot CLI."""
    from .copilot_runtime import CopilotRuntime
    from .logging import redact_secrets
    
    async def _run():
        rt = CopilotRuntime()
        try:
            await rt.start()
            try:
                st = await rt.client.get_status()
                auth = await rt.client.get_auth_status()
                console.print(Panel.fit(f"state={st.state}\ncliVersion={st.cliVersion}\n\n" +
                                        f"isAuthenticated={auth.isAuthenticated}\nlogin={auth.login}",
                                        title="Copilot SDK Status"))
            except Exception as e:
                console.print(f"[yellow]Could not get Copilot status: {redact_secrets(str(e))}[/yellow]")
        except Exception as e:
            console.print(f"[red]Failed to connect to Copilot SDK: {redact_secrets(str(e))}[/red]")
            raise typer.Exit(1)
        finally:
            await rt.stop()
    asyncio.run(_run())


@copilot_app.command("chat")
def copilot_chat(
    prompt: str,
    model: Optional[str] = None,
    timeout: int = typer.Option(120, help="Timeout in seconds"),
) -> None:
    """Send a single prompt and print the assistant response."""
    from .copilot_runtime import CopilotRuntime
    from .logging import redact_secrets
    
    async def _run():
        rt = CopilotRuntime(model=model)
        try:
            await rt.start()
            try:
                text = await rt.send_and_wait(prompt, timeout_s=timeout)
                console.print(text)
            except asyncio.TimeoutError:
                console.print(f"[yellow]Chat timed out after {timeout} seconds[/yellow]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]Chat error: {redact_secrets(str(e))}[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Failed to start Copilot: {redact_secrets(str(e))}[/red]")
            raise typer.Exit(1)
        finally:
            await rt.stop()
    asyncio.run(_run())


@agents_app.command("list")
def agents_list() -> None:
    """List all available agents."""
    agents = AgentRegistry.list_agents()

    table = Table(title="Available Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")

    for name, desc in agents:
        table.add_row(name, desc)

    console.print(table)

    missing = AgentRegistry.validate_required()
    if missing:
        console.print(f"[yellow]Warning: Missing required agents: {', '.join(missing)}[/yellow]")


@persona_app.command("list")
def persona_list() -> None:
    """List available personas."""
    from .personas import list_personas
    
    personas = list_personas()
    table = Table(title="Available Personas")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    
    for name, desc in personas:
        table.add_row(name, desc)
    
    console.print(table)


@valves_app.command("get")
def valves_get(key: str) -> None:
    """Get a configuration valve value."""
    value = ConfigManager.get_valve(key)
    if value is None:
        console.print(f"[yellow]Valve '{key}' not found[/yellow]")
    else:
        console.print(f"{key} = {json.dumps(value)}")


@valves_app.command("set")
def valves_set(key: str, value: str) -> None:
    """Set a configuration valve value."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value

    ConfigManager.set_valve(key, parsed)
    console.print(f"[green]Set {key} = {json.dumps(parsed)}[/green]")


@app.command("loop")
def loop(
    task: str,
    executor: str = typer.Option("copilot", help="copilot | jules | opencode"),
    max_retries: int = typer.Option(2, help="Max re-plans after FAIL"),
    workdir: Path = typer.Option(Path.cwd(), help="Repo working directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate plan but don't apply changes"),
    context: Optional[Path] = typer.Option(None, "--context", help="Path to inject into context (e.g., ./docs)"),
    persona: str = typer.Option("default", help="Persona to use (default, security, docs, refactor)"),
    no_live: bool = typer.Option(False, "--no-live", help="Disable streaming UI"),
) -> None:
    """Run: Plan -> execute handoffs -> audit -> PASS/FAIL (starter loop)."""
    config = ConfigManager.load_config()
    config.persona = persona
    ConfigManager.save_config(config)
    
    console.print(f"[cyan]Using persona: {persona}[/cyan]")
    
    context_content = ""
    if context:
        from .context import collect_context
        context_content = collect_context(context)
        if context_content:
            console.print(f"[cyan]Loaded context from {context}: {len(context_content)} chars[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow]")
        console.print(f"Task: {task}")
        console.print(f"Executor: {executor}")
        console.print("")
        
        async def _dry_run():
            from .orchestrator.loop import run_loop
            from .orchestrator.artifacts import TaskArtifact, sanitize_slug
            
            slug = sanitize_slug(task)
            artifact = TaskArtifact(slug=slug)
            artifact.content = f"# DRY RUN - Task: {task}\n\nGenerated: (dry run mode)\n"
            artifact.audit_content = "# DRY RUN\n\nNo execution performed.\n"
            artifact.save()
            
            result = await run_loop(
                task=task,
                executor=executor,
                max_retries=0,
                workdir=workdir,
                dry_run=True,
            )
            return result
        
        setup_global_logging()
        run_id = HeidiLogger.init_run()
        
        HeidiLogger.write_run_meta({
            "run_id": run_id,
            "task": task,
            "executor": executor,
            "max_retries": 0,
            "workdir": str(workdir),
            "dry_run": True,
        })
        
        import asyncio
        try:
            result = asyncio.run(_dry_run())
            console.print(Panel.fit("[yellow]DRY RUN COMPLETE[/yellow]\n\nArtifacts written to ./tasks/"))
            HeidiLogger.write_run_meta({"status": "dry_run", "result": result})
        except Exception as e:
            console.print(f"[red]Dry run failed: {e}[/red]")
            HeidiLogger.write_run_meta({"status": "dry_run_failed", "error": str(e)})
        return

    setup_global_logging()
    run_id = HeidiLogger.init_run()

    HeidiLogger.write_run_meta({
        "run_id": run_id,
        "task": task,
        "executor": executor,
        "max_retries": max_retries,
        "workdir": str(workdir),
    })

    console.print(f"[cyan]Starting loop {run_id}: {task}[/cyan]")
    HeidiLogger.emit_status(f"Loop started with executor={executor}")

    async def _run():
        try:
            result = await run_loop(task=task, executor=executor, max_retries=max_retries, workdir=workdir)
            HeidiLogger.emit_result(result)
            console.print(Panel.fit(result, title=f"Loop {run_id} Result"))
            HeidiLogger.write_run_meta({"status": "completed", "result": result})
        except Exception as e:
            error_msg = f"Loop failed: {e}"
            HeidiLogger.error(error_msg)
            HeidiLogger.write_run_meta({"status": "failed", "error": str(e)})
            console.print(f"[red]{error_msg}[/red]")
            raise typer.Exit(1)

    asyncio.run(_run())


@app.command("run")
def run(
    prompt: str,
    executor: str = typer.Option("copilot", help="copilot | jules | opencode"),
    workdir: Path = typer.Option(Path.cwd(), help="Repo working directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be executed"),
    context: Optional[Path] = typer.Option(None, "--context", help="Path to inject into context (e.g., ./docs)"),
) -> None:
    """Run a single prompt with the specified executor."""
    context_content = ""
    if context:
        from .context import collect_context
        context_content = collect_context(context)
        if context_content:
            console.print(f"[cyan]Loaded context from {context}: {len(context_content)} chars[/cyan]")
    
    if dry_run:
        console.print("[yellow]DRY RUN: Would execute:[/yellow]")
        console.print(f"  executor: {executor}")
        console.print(f"  prompt: {prompt[:100]}...")
        console.print(f"  workdir: {workdir}")
        console.print(f"  context: {context if context else 'none'}")
        return

    setup_global_logging()
    run_id = HeidiLogger.init_run()

    HeidiLogger.write_run_meta({
        "run_id": run_id,
        "prompt": prompt,
        "executor": executor,
        "workdir": str(workdir),
    })

    async def _run():
        exec_impl = _pick_executor(executor)
        try:
            result = await exec_impl.run(prompt, workdir)
            console.print(result.output)
            HeidiLogger.write_run_meta({"status": "completed", "ok": result.ok})
        except Exception as e:
            error_msg = f"Run failed: {e}"
            HeidiLogger.error(error_msg)
            HeidiLogger.write_run_meta({"status": "failed", "error": str(e)})
            raise typer.Exit(1)

    asyncio.run(_run())


@app.command("verify")
def verify(
    commands: list[str] = typer.Argument(..., help="Commands to verify"),
    workdir: Path = typer.Option(Path.cwd(), help="Working directory"),
) -> None:
    """Run verification commands and report results."""
    from .orchestrator.workspace import WorkspaceManager, VerificationRunner

    ws = WorkspaceManager(workdir)
    runner = VerificationRunner(ws)

    console.print(f"[cyan]Running {len(commands)} verification commands...[/cyan]")
    results = runner.run_commands(commands)

    table = Table(title="Verification Results")
    table.add_column("Command", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Output", style="white")

    all_passed = True
    for cmd, result in results.items():
        status = "PASS" if result["returncode"] == "0" else "FAIL"
        if status == "FAIL":
            all_passed = False
        output = result["stdout"][:100] or result["stderr"][:100] or ""
        table.add_row(cmd[:50], status, output)

    console.print(table)

    if all_passed:
        console.print("[green]All verifications passed[/green]")
    else:
        console.print("[red]Some verifications failed[/red]")
        raise typer.Exit(1)


@app.command("runs")
def runs_list(
    limit: int = typer.Option(10, help="Number of runs to show"),
) -> None:
    """List recent runs."""
    runs_dir = ConfigManager.runs_dir()
    if not runs_dir.exists():
        console.print("[yellow]No runs found[/yellow]")
        return

    runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    table = Table(title="Recent Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Task", style="white")

    for run_path in runs:
        run_json = run_path / "run.json"
        if run_json.exists():
            meta = json.loads(run_json.read_text())
            status = meta.get("status", "unknown")
            task = meta.get("task", meta.get("prompt", ""))[:50]
            table.add_row(run_path.name, status, task)
        else:
            table.add_row(run_path.name, "unknown", "")

    console.print(table)


@app.command("status")
def status_cmd() -> None:
    """Show Heidi CLI status and token usage."""
    from .token_usage import get_total_usage

    config = ConfigManager.load_config()
    token = ConfigManager.get_github_token()

    table = Table(title="Heidi CLI Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Provider", config.provider or "copilot")
    table.add_row("Telemetry", "enabled" if config.telemetry_enabled else "disabled")
    table.add_row("Server URL", config.server_url)
    table.add_row("GitHub Auth", "configured" if token else "not configured")

    console.print(table)

    usage = get_total_usage()
    if usage["runs"] > 0:
        usage_table = Table(title="Token Usage Summary")
        usage_table.add_column("Metric", style="cyan")
        usage_table.add_column("Value", style="white")
        usage_table.add_row("Total Runs", str(usage["runs"]))
        usage_table.add_row("Total Tokens", f"{usage['total_tokens']:,}")
        usage_table.add_row("Estimated Cost", f"${usage['total_cost']:.4f}")
        console.print(usage_table)
    else:
        console.print("[dim]No runs yet. Run 'heidi loop' to get started.[/dim]")


@app.command("restore")
def restore_cmd(
    path: Path = typer.Argument(..., help="File path to restore"),
    run_id: Optional[str] = typer.Option(None, help="Specific run ID to restore from"),
    latest: bool = typer.Option(True, help="Restore latest backup (vs earliest)"),
) -> None:
    """Restore a file from backup."""
    from .backup import restore_file
    
    if not path.exists() and run_id is None:
        console.print(f"[red]File '{path}' not found. Provide run_id to restore deleted file.[/red]")
        raise typer.Exit(1)
    
    success = restore_file(path, run_id, latest)
    if success:
        console.print(f"[green]Restored {path.name} from backup[/green]")
    else:
        console.print(f"[red]No backup found for {path.name}[/red]")
        raise typer.Exit(1)


@app.command("backups")
def backups_cmd(
    run_id: Optional[str] = typer.Option(None, help="Filter by run ID"),
) -> None:
    """List available backups."""
    from .backup import list_backups
    
    backups = list_backups(run_id)
    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return
    
    table = Table(title="Backups")
    table.add_column("File", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Size", style="white")
    
    for b in backups[:20]:
        table.add_row(b["name"], b["path"], f"{b['size']} bytes")
    
    console.print(table)


@app.command("serve")


@app.command("review")
def review_cmd(
    diff: bool = typer.Option(False, "--diff", help="Review current git diff"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Review diff against branch"),
) -> None:
    """Run AI code review on diff or branch."""
    import subprocess
    
    if not diff and not branch:
        console.print("[red]Specify --diff or --branch[/red]")
        raise typer.Exit(1)
    
    try:
        if diff:
            result = subprocess.run(["git", "diff"], capture_output=True, text=True)
            diff_text = result.stdout or result.stderr
        else:
            target_branch = branch or "main"
            result = subprocess.run(["git", "diff", f"main...{target_branch}"], capture_output=True, text=True)
            diff_text = result.stdout or result.stderr
        
        if not diff_text.strip():
            console.print("[yellow]No changes to review[/yellow]")
            return
        
        review_prompt = f"""You are a code reviewer. Review the following changes and provide feedback:

## Changes
{diff_text[:10000]}

Provide:
1. Summary (2-3 sentences)
2. High-risk findings (list any security, correctness, or performance concerns)
3. Actionable checklist (what should be fixed before merging)
"""
        console.print("[cyan]Generating review...[/cyan]")
        
        async def _run_review():
            from .orchestrator.loop import pick_executor
            exec_impl = pick_executor("copilot")
            result = await exec_impl.run(review_prompt, Path.cwd())
            return result
        
        import asyncio
        result = asyncio.run(_run_review())
        
        console.print(Panel.fit(result.output[:3000], title="Code Review"))
        
        review_file = Path("./reviews.md")
        review_file.write_text(f"# Code Review\n\n{result.output}")
        console.print(f"[green]Review saved to {review_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Review failed: {e}[/red]")
        raise typer.Exit(1)
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(7777, help="Port to bind to"),
) -> None:
    """Start Heidi CLI HTTP server for OpenWebUI integration."""
    from .server import start_server
    console.print(f"[green]Starting Heidi server on {host}:{port}[/green]")
    start_server(host=host, port=port)


if __name__ == "__main__":
    app()
