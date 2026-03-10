"""
Heidi API Key CLI Commands

Command-line interface for managing Heidi API keys.
"""

import typer
import json
from typing import Optional, List
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .key_manager import get_api_key_manager, APIKey
from ..shared.config import ConfigLoader

console = Console()
api_app = typer.Typer(name="api", help="Heidi API Key Management")


def register_api_app(main_app):
    """Register the API app with the main CLI app."""
    main_app.add_typer(api_app, name="api")


@api_app.command("generate")
def generate_api_key(
    name: str = typer.Option(..., "--name", "-n", help="Name for the API key"),
    user_id: str = typer.Option("default", "--user", "-u", help="User ID"),
    expires_days: Optional[int] = typer.Option(None, "--expires", "-e", help="Days until expiration"),
    rate_limit: int = typer.Option(100, "--rate-limit", "-r", help="Requests per minute"),
    permissions: Optional[str] = typer.Option("read,write", "--permissions", "-p", help="Permissions (comma-separated)")
):
    """Generate a new Heidi API key."""
    
    try:
        key_manager = get_api_key_manager()
        
        # Parse permissions
        perm_list = [p.strip() for p in permissions.split(",")]
        
        # Generate API key
        api_key = key_manager.generate_api_key(
            name=name,
            user_id=user_id,
            expires_days=expires_days,
            rate_limit=rate_limit,
            permissions=perm_list
        )
        
        # Display results
        console.print(Panel.fit(
            f"[bold green]✅ API Key Generated Successfully![/bold green]\n\n"
            f"[bold]Key ID:[/bold] {api_key.key_id}\n"
            f"[bold]Name:[/bold] {api_key.name}\n"
            f"[bold]User:[/bold] {api_key.user_id}\n"
            f"[bold]Created:[/bold] {api_key.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold]Expires:[/bold] {api_key.expires_at.strftime('%Y-%m-%d %H:%M:%S') if api_key.expires_at else 'Never'}\n"
            f"[bold]Rate Limit:[/bold] {api_key.rate_limit} requests/minute\n"
            f"[bold]Permissions:[/bold] {', '.join(api_key.permissions)}",
            title="🔑 Heidi API Key",
            border_style="green"
        ))
        
        # Show the API key (only once!)
        console.print("\n[bold yellow]⚠️  Save this API key securely - it will not be shown again![/bold yellow]")
        console.print(f"[bold blue]🔑 API Key:[/bold blue] [code]{api_key.api_key}[/code]")
        
        # Usage instructions
        console.print("\n[bold]📖 Usage Instructions:[/bold]")
        console.print("1. Use this key with any Heidi-compatible application")
        console.print("2. Set as environment variable: [code]export HEIDI_API_KEY=your_key[/code]")
        console.print("3. Or pass in Authorization header: [code]Authorization: Bearer your_key[/code]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to generate API key: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("list")
def list_api_keys(
    user_id: str = typer.Option("default", "--user", "-u", help="User ID")
):
    """List all API keys for a user."""
    
    try:
        key_manager = get_api_key_manager()
        keys = key_manager.list_api_keys(user_id)
        
        if not keys:
            console.print(f"[yellow]ℹ️  No API keys found for user: {user_id}[/yellow]")
            return
        
        # Create table
        table = Table(title=f"🔑 API Keys for {user_id}")
        table.add_column("Key ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Created", style="green")
        table.add_column("Expires", style="yellow")
        table.add_column("Status", style="red")
        table.add_column("Usage", style="blue")
        table.add_column("Rate Limit", style="white")
        
        for key in keys:
            status = "✅ Active" if key.is_valid else "❌ Inactive"
            expires = key.expires_at.strftime("%Y-%m-%d") if key.expires_at else "Never"
            
            table.add_row(
                key.key_id[:8] + "...",
                key.name,
                key.created_at.strftime("%Y-%m-%d"),
                expires,
                status,
                f"{key.usage_count} requests",
                f"{key.rate_limit}/min"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Failed to list API keys: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("revoke")
def revoke_api_key(
    key_id: str = typer.Argument(..., help="API Key ID to revoke")
):
    """Revoke an API key."""
    
    try:
        key_manager = get_api_key_manager()
        
        if key_manager.revoke_api_key(key_id):
            console.print(f"[green]✅ API key {key_id} has been revoked[/green]")
        else:
            console.print(f"[red]❌ API key {key_id} not found[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to revoke API key: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("stats")
def api_key_stats(
    key_id: str = typer.Argument(..., help="API Key ID")
):
    """Show usage statistics for an API key."""
    
    try:
        key_manager = get_api_key_manager()
        stats = key_manager.get_usage_stats(key_id)
        
        if not stats:
            console.print(f"[red]❌ API key {key_id} not found[/red]")
            raise typer.Exit(1)
        
        # Display stats
        console.print(Panel.fit(
            f"[bold]📊 Usage Statistics for {key_id}[/bold]\n\n"
            f"[bold]Total Requests:[/bold] {stats['usage_count']}\n"
            f"[bold]Created:[/bold] {stats['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold]Last Used:[/bold] {stats['last_used'].strftime('%Y-%m-%d %H:%M:%S') if stats['last_used'] else 'Never'}\n"
            f"[bold]Days Active:[/bold] {stats['days_active']}\n"
            f"[bold]Avg Daily Usage:[/bold] {stats['avg_daily_usage']:.2f} requests",
            title="📈 API Key Statistics",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get stats: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("models")
def list_available_models():
    """List all available models that can be accessed with Heidi API keys."""
    
    try:
        from .router import get_api_router
        router = get_api_router()
        models = router.list_available_models()
        
        # Display models by provider
        for provider, model_list in models.items():
            if not model_list:
                continue
                
            console.print(f"\n[bold]🤖 {provider.title()} Models:[/bold]")
            
            for model in model_list:
                console.print(f"  • [cyan]{model['id']}[/cyan]")
                console.print(f"    [dim]{model.get('description', 'No description')}[/dim]")
        
        console.print("\n[bold]📖 Usage Examples:[/bold]")
        console.print("• Local model: [code]local://my-model[/code]")
        console.print("• HuggingFace: [code]hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0[/code]")
        console.print("• OpenCode: [code]opencode://gpt-4[/code]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to list models: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("config")
def show_api_config():
    """Show current API configuration."""
    
    try:
        config = ConfigLoader.load()
        
        console.print(Panel.fit(
            f"[bold]⚙️  Heidi API Configuration[/bold]\n\n"
            f"[bold]API Enabled:[/bold] {getattr(config, 'api_enabled', False)}\n"
            f"[bold]API Host:[/bold] {getattr(config, 'api_host', '127.0.0.1')}\n"
            f"[bold]API Port:[/bold] {getattr(config, 'api_port', 8000)}\n"
            f"[bold]Default Rate Limit:[/bold] {getattr(config, 'default_rate_limit', 100)}\n"
            f"[bold]Analytics Enabled:[/bold] {getattr(config, 'analytics_enabled', True)}\n"
            f"[bold]Token Tracking Enabled:[/bold] {getattr(config, 'token_tracking_enabled', True)}",
            title="🔧 API Configuration",
            border_style="cyan"
        ))
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get configuration: {e}[/red]")
        raise typer.Exit(1)


@api_app.command("server")
def start_api_server(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes")
):
    """Start the Heidi API server."""
    
    try:
        console.print(f"[green]🚀 Starting Heidi API Server...[/green]")
        console.print(f"[blue]🌐 Host:[/blue] {host}")
        console.print(f"[blue]🔌 Port:[/blue] {port}")
        console.print(f"[blue]👥 Workers:[/blue] {workers}")
        
        # This would start the actual FastAPI server
        # For now, just show the configuration
        console.print(f"\n[yellow]⚠️  API server startup not implemented in this demo[/yellow]")
        console.print(f"[dim]In production, this would start a FastAPI server with:[/dim]")
        console.print(f"[dim]• Authentication middleware[/dim]")
        console.print(f"[dim]• Rate limiting[/dim]")
        console.print(f"[dim]• Request routing[/dim]")
        console.print(f"[dim]• Usage analytics[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to start server: {e}[/red]")
        raise typer.Exit(1)
