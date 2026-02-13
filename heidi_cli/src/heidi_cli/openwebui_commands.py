from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

from .config import ConfigManager

console = Console()

openwebui_app = typer.Typer(help="OpenWebUI integration commands")


def _test_openwebui_connection(url: str, token: str | None = None) -> tuple[bool, str]:
    """Test OpenWebUI connection and return (success, message)."""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Test the /api/models endpoint as documented
        response = httpx.get(f"{url}/api/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "OpenWebUI API: OK"
        elif response.status_code == 401:
            return False, "OpenWebUI API: Token invalid"
        else:
            return False, f"OpenWebUI API: HTTP {response.status_code}"
    except httpx.ConnectError:
        return False, "OpenWebUI API: Connection refused (not running?)"
    except Exception as e:
        return False, f"OpenWebUI API: Error - {e}"


@openwebui_app.command("status")
def openwebui_status() -> None:
    """Check OpenWebUI connectivity and authentication. Returns exit codes:
    - 0: OK
    - 1: not configured
    - 2: unreachable
    - 3: unauthorized
    """
    config = ConfigManager.load_config()
    
    # Get OpenWebUI URL from config or use default
    openwebui_url = getattr(config, 'openwebui_url', 'http://localhost:3000')
    openwebui_token = getattr(config, 'openwebui_token', None)
    
    if not openwebui_url:
        console.print("[yellow]OpenWebUI not configured[/yellow]")
        raise typer.Exit(1)
    
    # Test connection
    success, message = _test_openwebui_connection(openwebui_url, openwebui_token)
    
    # Print single-line status
    if success:
        console.print(f"[green]✅ {message}[/green]")
        raise typer.Exit(0)
    else:
        console.print(f"[red]❌ {message}[/red]")
        
        # Determine exit code based on error type
        if "unauthorized" in message.lower() or "401" in message:
            raise typer.Exit(3)
        elif "connection refused" in message.lower() or "not running" in message.lower():
            raise typer.Exit(2)
        else:
            raise typer.Exit(2)


@openwebui_app.command("guide")
def openwebui_guide() -> None:
    """Print exact OpenWebUI connection instructions + URLs (no network calls)."""
    console.print(Panel.fit(
        "[bold cyan]OpenWebUI Integration Guide[/bold cyan]\n\n"
        "To connect Heidi CLI as OpenAPI tools in OpenWebUI:\n\n"
        "1. Open OpenWebUI in your browser\n"
        "2. Navigate to: [cyan]Settings → Connections → OpenAPI Servers[/cyan]\n"
        "3. Click [bold]Add Server[/bold] and configure:\n"
        "   • Name: [green]Heidi CLI[/green]\n"
        "   • OpenAPI Spec URL: [green]http://localhost:7777/openapi.json[/green]\n"
        "4. Save and test the connection",
        title="OpenWebUI Configuration"
    ))
    
    console.print("\n[bold]Quick Test URLs:[/bold]")
    console.print("• Health: http://localhost:7777/health")
    console.print("• Agents: http://localhost:7777/agents")
    console.print("• Runs: http://localhost:7777/runs")
    console.print("• Stream: http://localhost:7777/runs/<id>/stream (SSE)")


@openwebui_app.command("configure")
def openwebui_configure(
    url: str = typer.Option("http://localhost:3000", help="OpenWebUI URL"),
    token: str = typer.Option(None, help="OpenWebUI API token"),
) -> None:
    """Configure OpenWebUI settings."""
    config = ConfigManager.load_config()
    
    # Store OpenWebUI settings
    config.openwebui_url = url
    if token:
        config.openwebui_token = token
    
    ConfigManager.save_config(config)
    
    console.print("[green]OpenWebUI configured[/green]")
    console.print(f"URL: {url}")
    console.print(f"Token: {'[green]configured[/green]' if token else '[yellow]not set[/yellow]'}")
    
    # Test connection
    console.print("\nTesting connection...")
    success, message = _test_openwebui_connection(url, token)
    
    if success:
        console.print(f"[green]✅ {message}[/green]")
    else:
        console.print(f"[red]❌ {message}[/red]")
        console.print("\n[yellow]Tip: Make sure OpenWebUI is running and accessible[/yellow]")