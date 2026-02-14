from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
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

app = typer.Typer(
    add_completion=False,
    help="Heidi CLI - Copilot/Jules/OpenCode orchestrator",
    epilog="""
Common commands:
  heidi start ui       Start UI dev server (port 3002)
  heidi start backend  Start backend API server (port 7777)
  heidi copilot chat   Chat with GitHub Copilot
  heidi setup          Interactive first-time setup
""",
)
copilot_app = typer.Typer(help="Copilot (Copilot CLI via GitHub Copilot SDK)")
auth_app = typer.Typer(help="Authentication commands")
agents_app = typer.Typer(help="Agent management")
valves_app = typer.Typer(help="Configuration valves")
persona_app = typer.Typer(help="Persona management")
start_app = typer.Typer(help="Start services (UI, backend, etc.)", no_args_is_help=True)

app.add_typer(copilot_app, name="copilot")
app.add_typer(auth_app, name="auth")
app.add_typer(agents_app, name="agents")
app.add_typer(valves_app, name="valves")
app.add_typer(openwebui_app, name="openwebui")
app.add_typer(persona_app, name="persona")
app.add_typer(start_app, name="start")

console = Console()
json_output = False
verbose_mode = False


def get_version() -> str:
    from . import __version__

    return __version__


def print_json(data: Any) -> None:
    if json_output:
        print(json.dumps(data, indent=2))


def open_url(url: str) -> None:
    """Open URL in browser - WSL/Linux/Windows compatible."""
    if sys.platform == "win32":
        subprocess.run(["powershell.exe", "-Command", f"Start-Process '{url}'"], check=False)
        return
    elif shutil.which("wslview"):
        subprocess.run(["wslview", url], check=False)
        return
    elif shutil.which("sensible-browser"):
        subprocess.run(["sensible-browser", url], check=False)
        return
    elif shutil.which("xdg-open"):
        subprocess.run(["xdg-open", url], check=False)
        return
    elif shutil.which("gnome-open"):
        subprocess.run(["gnome-open", url], check=False)
        return
    elif shutil.which("gio"):
        result = subprocess.run(["gio", "open", url], check=False)
        if result.returncode == 0:
            return

    # Try webbrowser as last resort
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        console.print("[yellow]Could not open browser automatically.[/yellow]")
        console.print(f"[cyan]Open manually: {url}[/cyan]")


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

    import os
    import sys

    # Skip wizard for start commands
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        return

    # Skip wizard for read-only commands that don't require config
    if len(sys.argv) > 1 and sys.argv[1] in ("paths", "doctor"):
        return

    if not ConfigManager.config_file().exists() and not os.environ.get("HEIDI_NO_WIZARD"):
        console.print(
            Panel.fit(
                "[yellow]Heidi CLI is not initialized yet.[/yellow]\n\nStarting setup wizard...",
                title="First Time Setup",
            )
        )
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
def paths() -> None:
    """Show where Heidi stores configuration and data."""
    from .config import (
        ConfigManager,
        check_legacy_heidi_dir,
        heidi_config_dir,
        heidi_state_dir,
        heidi_cache_dir,
    )

    ConfigManager.ensure_dirs()

    table = Table(title="Heidi CLI Paths")
    table.add_column("Location", style="cyan")
    table.add_column("Path", style="white")

    table.add_row("Config (global)", str(heidi_config_dir()))

    state_dir = heidi_state_dir()
    if state_dir:
        table.add_row("State (global)", str(state_dir))

    cache_dir = heidi_cache_dir()
    if cache_dir:
        table.add_row("Cache (global)", str(cache_dir))

    table.add_row("Project Root", str(ConfigManager.project_root()))
    table.add_row("Tasks (project)", str(ConfigManager.tasks_dir()))

    console.print(table)

    legacy = check_legacy_heidi_dir()
    if legacy:
        console.print(f"[yellow]Warning: Found legacy ./.heidi/ at {legacy}[/yellow]")
        console.print(
            "[dim]New default is {}. Run 'heidi migrate' to move config.[/dim]".format(
                heidi_config_dir()
            )
        )


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
    console.print(f"[green]Initialized Heidi at {ConfigManager.config_dir()}[/green]")
    console.print(f"  Config: {ConfigManager.config_file()}")
    console.print(f"  Secrets: {ConfigManager.secrets_file()}")
    console.print(f"  Runs: {ConfigManager.runs_dir()}")
    console.print(f"  Tasks: {ConfigManager.tasks_dir()}")


@app.command()
def update(
    no_ui: bool = typer.Option(False, "--no-ui", help="Skip UI update"),
) -> None:
    """Update UI and optional components to latest version."""
    from .config import heidi_ui_dir
    from .launcher import ensure_ui_repo

    console.print("[cyan]Running heidi update...[/cyan]")

    if not no_ui:
        console.print("\n[cyan]Updating UI...[/cyan]")
        ui_dir = heidi_ui_dir()
        ensure_ui_repo(ui_dir, no_update=False)
    else:
        console.print("[dim]Skipping UI update (--no-ui)[/dim]")

    console.print("\n[green]Update complete![/green]")


@app.command()
def upgrade() -> None:
    """Upgrade Heidi CLI to latest version."""
    console.print("[cyan]Running heidi upgrade...[/cyan]")

    # Detect install method
    # Check if pipx
    pipx_which = shutil.which("pipx")
    is_pipx = pipx_which is not None

    # Check if editable install (git checkout)
    import heidi_cli

    cli_path = Path(heidi_cli.__file__).parent
    is_git_checkout = (cli_path.parent / ".git").exists()

    if is_pipx:
        console.print("[cyan]Upgrading via pipx...[/cyan]")
        result = subprocess.run(["pipx", "upgrade", "heidi-cli"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]pipx upgrade failed: {result.stderr}[/red]")
            raise typer.Exit(1)
    elif is_git_checkout:
        console.print("[cyan]Upgrading from git checkout...[/cyan]")
        # Try git pull
        result = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=str(cli_path.parent),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[yellow]Git pull failed: {result.stderr}[/yellow]")

        # Reinstall in editable mode
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"],
            cwd=str(cli_path.parent),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]pip install failed: {result.stderr}[/red]")
            raise typer.Exit(1)
    else:
        # Regular pip install
        console.print("[cyan]Upgrading via pip...[/cyan]")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "heidi-cli", "-q"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]pip upgrade failed: {result.stderr}[/red]")
            raise typer.Exit(1)

    console.print("[green]Upgrade complete![/green]")
    console.print("[dim]Run 'heidi update' to update UI and other components.[/dim]")


@app.command()
def uninstall(
    purge: bool = typer.Option(False, "--purge", help="Also remove all config, state, and cache"),
) -> None:
    """Uninstall Heidi CLI."""
    import shutil as _shutil
    from .config import heidi_config_dir, heidi_state_dir, heidi_cache_dir, heidi_ui_dir

    if not purge:
        console.print("[yellow]This will remove Heidi CLI but keep config/state/cache.[/yellow]")
        console.print("[dim]Use --purge to remove everything.[/dim]")

    console.print("\n[cyan]Stopping services...[/cyan]")
    # Try to stop any running services
    try:
        from .launcher import stop_all

        stop_all()
    except Exception:
        pass

    # Detect and remove CLI
    cli_path = Path(__file__).parent
    is_git_checkout = (cli_path.parent / ".git").exists()
    is_pipx = _shutil.which("pipx") is not None

    if is_pipx:
        console.print("[cyan]Removing via pipx...[/cyan]")
        subprocess.run(["pipx", "uninstall", "heidi-cli"], capture_output=True)
    elif is_git_checkout:
        console.print("[yellow]Heidi was installed via git clone.[/yellow]")
        console.print(f"[dim]Remove manually: rm -rf {cli_path.parent.parent}[/dim]")
    else:
        console.print("[cyan]Removing via pip...[/cyan]")
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "heidi-cli", "-y"], capture_output=True
        )

    if purge:
        console.print("\n[cyan]Removing config, state, cache...[/cyan]")
        for path in [heidi_config_dir(), heidi_state_dir(), heidi_cache_dir(), heidi_ui_dir()]:
            if path and path.exists():
                console.print(f"  Removing {path}")
                import shutil

                try:
                    shutil.rmtree(path)
                except Exception as e:
                    console.print(f"  [yellow]Failed to remove {path}: {e}[/yellow]")

    console.print("\n[green]Heidi CLI uninstalled![/green]")
    if not purge:
        console.print("[dim]Config/state/cached at:[/dim]")
        console.print(f"  Config: {heidi_config_dir()}")
        if heidi_state_dir():
            console.print(f"  State: {heidi_state_dir()}")
        if heidi_cache_dir():
            console.print(f"  Cache: {heidi_cache_dir()}")


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

    config_dir = ConfigManager.config_dir()
    tasks_dir = ConfigManager.tasks_dir()
    if config_dir.exists():
        checks.append(("Config dir", "ok", str(config_dir)))
    else:
        checks.append(("Config dir", "warning", "not initialized (run heidi init)"))

    if tasks_dir.exists():
        checks.append(("Tasks dir", "ok", str(tasks_dir)))
    else:
        checks.append(("Tasks dir", "warning", "not created yet"))

    config = ConfigManager.load_config()
    checks.append(
        (
            "Telemetry",
            "enabled" if config.telemetry_enabled else "disabled",
            f"telemetry_enabled={config.telemetry_enabled}",
        )
    )
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
    device: bool = typer.Option(False, "--device", help="Use device flow authentication"),
) -> None:
    """Authenticate with GitHub for Copilot access."""
    if device:
        from .auth_device import login_with_device_flow

        access_token = login_with_device_flow()
        if not access_token:
            raise typer.Exit(1)
        token = access_token

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
                table.add_row("CLI Version", str(getattr(st, "cliVersion", "unknown")))
            except Exception as e:
                error_msg = str(e).lower()
                if (
                    "unauthorized" in error_msg
                    or "permission" in error_msg
                    or "copilot" in error_msg
                ):
                    table.add_row("CLI State", "[yellow]needs token[/yellow]")
                    console.print(
                        "\n[yellow]Copilot requires a GitHub token with Copilot permissions.[/yellow]"
                    )
                    console.print("[dim]Options:[/dim]")
                    console.print("1. Run: [cyan]heidi auth gh --device[/cyan] for device flow")
                    console.print("2. Or create a fine-grained PAT:")
                    console.print(
                        "   - Go to: https://github.com/settings/tokens/new?scopes=copilot"
                    )
                    console.print("   - Select 'copilot' permission")
                    console.print("   - Paste the token when prompted")
                else:
                    table.add_row("CLI State", "error")

            try:
                auth = await rt.client.get_auth_status()
                table.add_row("Authenticated", str(getattr(auth, "isAuthenticated", False)))
                table.add_row("Login", str(getattr(auth, "login", "unknown")))
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

    # Check for env var override
    if os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"):
        console.print("[yellow]Warning: GH_TOKEN or GITHUB_TOKEN env var is set.[/yellow]")
        console.print(
            "[yellow]This overrides OAuth token. Copilot may fail if env var token lacks Copilot scope.[/yellow]"
        )
        console.print()

    async def _run():
        rt = CopilotRuntime()
        try:
            await rt.start()
            try:
                st = await rt.client.get_status()
                auth = await rt.client.get_auth_status()
                console.print(
                    Panel.fit(
                        f"state={st.state}\ncliVersion={st.cliVersion}\n\n"
                        + f"isAuthenticated={auth.isAuthenticated}\nlogin={auth.login}",
                        title="Copilot SDK Status",
                    )
                )
            except Exception as e:
                console.print(
                    f"[yellow]Could not get Copilot status: {redact_secrets(str(e))}[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]Failed to connect to Copilot SDK: {redact_secrets(str(e))}[/red]")
            raise typer.Exit(1)
        finally:
            await rt.stop()

    asyncio.run(_run())


@copilot_app.command("login")
def copilot_login(
    use_gh: bool = typer.Option(True, "--gh/--pat", help="Use GH CLI OAuth (default) or PAT"),
    token: Optional[str] = typer.Option(None, "--token", help="PAT token (only if --pat)"),
    store_keyring: bool = typer.Option(True, help="Store token in OS keyring"),
) -> None:
    """Authenticate with GitHub for Copilot using OAuth (GH CLI) or PAT."""
    import shutil as _shutil

    gh_path = _shutil.which("gh")

    if os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"):
        console.print(
            "[yellow]Warning: GH_TOKEN or GITHUB_TOKEN environment variable is set.[/yellow]"
        )
        console.print("[yellow]This will override your OAuth token and Copilot may fail.[/yellow]")
        console.print("[dim]Either unset the env var or use --pat with a different token.[/dim]")
        console.print()

    token_used_source = None

    if use_gh:
        if not gh_path:
            console.print("[cyan]GitHub CLI not found → falling back to PAT mode[/cyan]")
            use_gh = False
        else:
            console.print("[cyan]Starting GitHub OAuth login via GH CLI...[/cyan]")
            console.print("[dim]This will open a browser window for authentication.[/dim]")

            try:
                result = subprocess.run(
                    ["gh", "auth", "login", "--web"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    console.print(f"[red]GH auth login failed: {result.stderr}[/red]")
                    console.print("[cyan]Falling back to PAT mode...[/cyan]")
                    use_gh = False
                else:
                    token_result = subprocess.run(
                        ["gh", "auth", "token"],
                        capture_output=True,
                        text=True,
                    )
                    if token_result.returncode != 0:
                        console.print(f"[red]Failed to get token: {token_result.stderr}[/red]")
                        console.print("[cyan]Falling back to PAT mode...[/cyan]")
                        use_gh = False
                    else:
                        token = token_result.stdout.strip()
                        if not token:
                            console.print("[red]No token returned from gh auth token[/red]")
                            console.print("[cyan]Falling back to PAT mode...[/cyan]")
                            use_gh = False
                        else:
                            token_used_source = "gh auth token"

            except subprocess.TimeoutExpired:
                console.print("[red]GH auth login timed out[/red]")
                console.print("[cyan]Falling back to PAT mode...[/cyan]")
                use_gh = False
            except FileNotFoundError:
                console.print("[red]GH CLI not found at runtime[/red]")
                console.print("[cyan]Falling back to PAT mode...[/cyan]")
                use_gh = False
            except Exception as e:
                console.print(f"[red]GH auth error: {e}[/red]")
                console.print("[cyan]Falling back to PAT mode...[/cyan]")
                use_gh = False

    if not use_gh or not token:
        env_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if env_token:
            token = env_token
            token_used_source = "GH_TOKEN/GITHUB_TOKEN env var"
            console.print("[dim]Using token from environment variable[/dim]")
        elif token:
            token_used_source = "--token argument"
        else:
            if not token:
                token = typer.prompt(
                    "Enter GitHub fine-grained PAT (with Copilot:read permission)",
                    hide_input=True,
                )
            if not token:
                console.print("[red]Token required[/red]")
                raise typer.Exit(1)
            token_used_source = "interactive prompt"

    if not token:
        console.print("[red]Token required[/red]")
        raise typer.Exit(1)

    ConfigManager.set_github_token(token, store_keyring=store_keyring)

    source_msg = f"Token source: {token_used_source}" if token_used_source else ""
    console.print("[green]GitHub token stored successfully[/green]")
    if store_keyring:
        console.print("[dim]Token stored in OS keyring[/dim]")
    else:
        console.print("[dim]Token stored only in secrets file (0600 perms)[/dim]")
    if source_msg:
        console.print(f"[dim]{source_msg}[/dim]")

    console.print()
    console.print("[cyan]To verify authentication, run:[/cyan]")
    console.print("  heidi copilot status")


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
    context: Optional[Path] = typer.Option(
        None, "--context", help="Path to inject into context (e.g., ./docs)"
    ),
    persona: str = typer.Option(
        "default", help="Persona to use (default, security, docs, refactor)"
    ),
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
            console.print(
                f"[cyan]Loaded context from {context}: {len(context_content)} chars[/cyan]"
            )
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

        HeidiLogger.write_run_meta(
            {
                "run_id": run_id,
                "task": task,
                "executor": executor,
                "max_retries": 0,
                "workdir": str(workdir),
                "dry_run": True,
            }
        )

        import asyncio

        try:
            result = asyncio.run(_dry_run())
            console.print(
                Panel.fit("[yellow]DRY RUN COMPLETE[/yellow]\n\nArtifacts written to ./tasks/")
            )
            HeidiLogger.write_run_meta({"status": "dry_run", "result": result})
        except Exception as e:
            console.print(f"[red]Dry run failed: {e}[/red]")
            HeidiLogger.write_run_meta({"status": "dry_run_failed", "error": str(e)})
        return

    setup_global_logging()
    run_id = HeidiLogger.init_run()

    HeidiLogger.write_run_meta(
        {
            "run_id": run_id,
            "task": task,
            "executor": executor,
            "max_retries": max_retries,
            "workdir": str(workdir),
        }
    )

    console.print(f"[cyan]Starting loop {run_id}: {task}[/cyan]")
    HeidiLogger.emit_status(f"Loop started with executor={executor}")

    async def _run():
        try:
            result = await run_loop(
                task=task, executor=executor, max_retries=max_retries, workdir=workdir
            )
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
    context: Optional[Path] = typer.Option(
        None, "--context", help="Path to inject into context (e.g., ./docs)"
    ),
) -> None:
    """Run a single prompt with the specified executor."""
    context_content = ""
    if context:
        from .context import collect_context

        context_content = collect_context(context)
        if context_content:
            console.print(
                f"[cyan]Loaded context from {context}: {len(context_content)} chars[/cyan]"
            )

    if dry_run:
        console.print("[yellow]DRY RUN: Would execute:[/yellow]")
        console.print(f"  executor: {executor}")
        console.print(f"  prompt: {prompt[:100]}...")
        console.print(f"  workdir: {workdir}")
        console.print(f"  context: {context if context else 'none'}")
        return

    setup_global_logging()
    run_id = HeidiLogger.init_run()

    HeidiLogger.write_run_meta(
        {
            "run_id": run_id,
            "prompt": prompt,
            "executor": executor,
            "workdir": str(workdir),
        }
    )

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
        console.print(
            f"[red]File '{path}' not found. Provide run_id to restore deleted file.[/red]"
        )
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
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(7777, help="Port to bind to"),
    ui: bool = typer.Option(False, "--ui", help="Also start UI dev server"),
) -> None:
    """Start Heidi CLI server."""
    import subprocess
    import threading

    def start_backend():
        from .server import start_server

        start_server(host=host, port=port)

    console.print(f"[cyan]Starting Heidi backend on {host}:{port}...[/cyan]")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    if ui:
        ui_path = Path.cwd() / "ui"
        if not ui_path.exists():
            console.print("[red]UI not found at ./ui - run from heidi-cli root[/red]")
            raise typer.Exit(1)

        console.print("[cyan]Starting UI dev server on http://localhost:3000...[/cyan]")

        def start_ui():
            subprocess.run(
                ["npm", "run", "dev", "--", "--port", "3000"],
                cwd=ui_path,
                env={**os.environ, "API_URL": f"http://{host}:{port}"},
            )

        ui_thread = threading.Thread(target=start_ui, daemon=True)
        ui_thread.start()

        console.print(
            Panel.fit(
                "[green]Heidi is running!\n\n"
                "Backend: http://localhost:7777\n"
                "UI: http://localhost:3000\n\n"
                "Press Ctrl+C to stop",
                title="Heidi CLI",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[green]Heidi server running at http://{host}:{port}[/green]\n\n"
                "Press Ctrl+C to stop",
                title="Heidi CLI Server",
            )
        )

    try:
        backend_thread.join()
    except KeyboardInterrupt:
        console.print("[yellow]Stopping Heidi...[/yellow]")


@app.command("ui")
def ui_cmd(
    backend: bool = typer.Option(True, "--backend/--no-backend", help="Start backend server"),
    ui: bool = typer.Option(True, "--ui/--no-ui", help="Start UI dev server"),
    port: int = typer.Option(7777, "--port", help="Backend port"),
    ui_port: int = typer.Option(3002, "--ui-port", help="UI dev server port"),
    ui_dir: Optional[str] = typer.Option(
        None,
        "--ui-dir",
        help="UI directory (clone: git clone https://github.com/heidi-dang/Heidi-cli-ui ui)",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
) -> None:
    """Start Heidi UI (shorthand for 'heidi start ui')."""
    from pathlib import Path
    from .launcher import (
        start_backend,
        start_ui_dev_server,
        is_backend_running,
        is_ui_running,
        stop_backend,
        stop_ui,
    )
    from rich.panel import Panel
    import signal
    import sys
    import os

    os.environ["HEIDI_NO_WIZARD"] = "1"
    ui_dir_path = Path(ui_dir) if ui_dir else None

    backend_process = None
    ui_process = None
    actual_port = port

    try:
        if backend:
            if is_backend_running("127.0.0.1", port):
                console.print(
                    f"[yellow]Backend already running on http://127.0.0.1:{port}[/yellow]"
                )
            else:
                backend_process, actual_port = start_backend(
                    host="127.0.0.1", port=port, wait=True, timeout=15
                )

        if ui:
            api_base = f"http://localhost:{actual_port}"
            if is_ui_running(ui_port):
                console.print(f"[yellow]UI already running on http://127.0.0.1:{ui_port}[/yellow]")
            else:
                ui_process = start_ui_dev_server(port=ui_port, api_url=api_base, ui_dir=ui_dir_path)

        api_url_final = f"http://127.0.0.1:{actual_port}"
        ui_url = f"http://127.0.0.1:{ui_port}"

        console.print(
            Panel.fit(
                f"[green]Backend:[/green] {api_url_final}\n[green]UI:[/green] {ui_url}",
                title="Heidi Services",
            )
        )

        if open_browser and ui:
            console.print("[cyan]Opening browser...[/cyan]")
            open_url(ui_url)

        console.print("\n[cyan]Press Ctrl+C to stop[/cyan]")

        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down...[/yellow]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        import time

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if ui_process:
            stop_ui()
        if backend_process:
            stop_backend()


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
            result = subprocess.run(
                ["git", "diff", f"main...{target_branch}"], capture_output=True, text=True
            )
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


@start_app.command("ui", help="Start UI dev server (default port 3002)")
def start_ui(
    backend: bool = typer.Option(True, "--backend/--no-backend", help="Start backend server"),
    ui: bool = typer.Option(True, "--ui/--no-ui", help="Start UI dev server"),
    port: int = typer.Option(7777, "--port", help="Backend port"),
    ui_port: int = typer.Option(3002, "--ui-port", help="UI dev server port"),
    ui_dir: Optional[str] = typer.Option(
        None,
        "--ui-dir",
        help="UI directory (default: auto-managed in cache dir)",
    ),
    no_ui_update: bool = typer.Option(
        False,
        "--no-ui-update",
        help="Skip auto-update of UI repo",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
    tunnel: bool = typer.Option(False, "--tunnel", help="Start Cloudflare tunnel"),
    api_url: str = typer.Option(
        "", "--api-url", help="API URL for UI (default: http://localhost:PORT)"
    ),
) -> None:
    """Start Heidi backend and UI dev server."""
    from pathlib import Path

    from .config import heidi_ui_dir
    from .launcher import (
        ensure_ui_repo,
        start_backend,
        start_ui_dev_server,
        is_backend_running,
        is_ui_running,
        stop_backend,
        stop_ui,
    )

    # Use provided ui_dir or default to heidi_ui_dir()
    if ui_dir:
        ui_dir_path = Path(ui_dir)
    else:
        ui_dir_path = heidi_ui_dir()
        console.print(f"[dim]Using UI directory: {ui_dir_path}[/dim]")
    from .tunnel import start_tunnel, stop_tunnel, is_cloudflared_installed, get_tunnel_instructions
    from rich.panel import Panel
    import signal
    import sys

    backend_process = None
    ui_process = None
    tunnel_process = None
    actual_port = port

    try:
        if backend:
            if is_backend_running("127.0.0.1", port):
                console.print(
                    f"[yellow]Backend already running on http://127.0.0.1:{port}[/yellow]"
                )
            else:
                backend_process, actual_port = start_backend(
                    host="127.0.0.1", port=port, wait=True, timeout=15
                )

        if ui:
            # Ensure UI repo exists and is up-to-date
            if not ui_dir_path.exists():
                ensure_result = ensure_ui_repo(ui_dir_path, no_ui_update)
                if ensure_result is None:
                    console.print("[red]Failed to get UI repo[/red]")
                    raise typer.Exit(1)

            api_base = api_url if api_url else f"http://localhost:{actual_port}"
            if is_ui_running(ui_port):
                console.print(f"[yellow]UI already running on http://127.0.0.1:{ui_port}[/yellow]")
            else:
                ui_process = start_ui_dev_server(port=ui_port, api_url=api_base, ui_dir=ui_dir_path)

        api_url_final = f"http://127.0.0.1:{actual_port}"
        ui_url = f"http://127.0.0.1:{ui_port}"

        console.print(
            Panel.fit(
                f"[green]Backend:[/green] {api_url_final}\n[green]UI:[/green] {ui_url}",
                title="Heidi Services",
            )
        )

        if open_browser and ui:
            console.print("[cyan]Opening browser...[/cyan]")
            open_url(ui_url)

        if not tunnel:
            tunnel = typer.confirm(
                "Expose publicly via Cloudflare Tunnel (cloudflared)?",
                default=False,
            )

        if tunnel:
            if not is_cloudflared_installed():
                console.print(get_tunnel_instructions())
            else:
                tunnel_process, public_url = start_tunnel(api_url_final)
                if public_url:
                    console.print(
                        Panel.fit(
                            f"[green]Public API:[/green] {public_url}\n"
                            f"[dim]Use this URL in UI Settings if needed[/dim]",
                            title="Cloudflare Tunnel",
                        )
                    )
                    if open_browser:
                        public_ui_url = f"{public_url}/?baseUrl={public_url}"
                        open_url(public_ui_url)

        console.print("\n[cyan]Press Ctrl+C to stop[/cyan]")

        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down...[/yellow]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        import time

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if tunnel_process:
            stop_tunnel(tunnel_process)
        if ui_process or is_ui_running(ui_port):
            stop_ui()
        if backend_process or is_backend_running("127.0.0.1", port):
            stop_backend()
        console.print("[green]Stopped.[/green]")


@start_app.command("backend")
def start_backend_cmd(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(7777, "--port", help="Port to bind to"),
    open_browser: bool = typer.Option(False, "--open/--no-open", help="Open browser automatically"),
) -> None:
    """Start the Heidi API server only."""
    from .launcher import start_backend, is_backend_running

    if is_backend_running(host, port):
        console.print(f"[yellow]Backend already running on http://{host}:{port}[/yellow]")
        return

    process, actual_port = start_backend(host=host, port=port, wait=True, timeout=15)

    console.print(f"[green]Backend running at http://{host}:{actual_port}[/green]")

    if open_browser:
        open_url(f"http://{host}:{actual_port}/ui/")


@start_app.command("services")
def services_status_cmd() -> None:
    """Show status of Heidi services."""
    from .launcher import get_status
    from rich.table import Table

    status = get_status()

    if not status:
        console.print("[yellow]No Heidi services running[/yellow]")
        return

    table = Table(title="Heidi Services Status")
    table.add_column("Service", style="cyan")
    table.add_column("PID", style="yellow")
    table.add_column("Running", style="green")
    table.add_column("Port", style="magenta")

    for name, info in status.items():
        running = "Yes" if info.get("running") else "No"
        style = "green" if info.get("running") else "red"
        table.add_row(
            name,
            str(info.get("pid", "N/A")),
            f"[{style}]{running}[/{style}]",
            str(info.get("port", "N/A")),
        )

    console.print(table)


@start_app.command("stop")
def stop_cmd(
    all: bool = typer.Option(True, "--all", help="Stop all services"),
    backend: bool = typer.Option(False, "--backend", help="Stop backend only"),
    ui: bool = typer.Option(False, "--ui", help="Stop UI only"),
) -> None:
    """Stop Heidi services."""
    from .launcher import stop_backend, stop_ui, stop_all, get_status

    status = get_status()

    if not status:
        console.print("[yellow]No services running[/yellow]")
        return

    if all or (not backend and not ui):
        console.print("[cyan]Stopping all services...[/cyan]")
        stop_all()
    else:
        if backend and "backend" in status:
            stop_backend()
        if ui and "ui" in status:
            stop_ui()

    console.print("[green]Done.[/green]")


@start_app.command("server")
def start_server_cmd(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(7777, "--port", help="Port to bind to"),
) -> None:
    """Start the Heidi API server only (without UI)."""
    from .server import start_server

    start_server(host=host, port=port)


if __name__ == "__main__":
    app()
