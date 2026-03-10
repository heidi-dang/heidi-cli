"""
Token tracking CLI commands.
"""

from __future__ import annotations

import sqlite3
import typer
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..token_tracking.models import get_token_database, TokenUsage, CostConfig
from ..shared.config import ConfigLoader

console = Console()
tokens_app = typer.Typer(help="Token tracking and cost management")


@tokens_app.command("history")
def token_history(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of recent records to show"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Filter by model ID"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user ID"),
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Filter by last N days"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON")
) -> None:
    """Show token usage history."""
    
    db = get_token_database()
    
    # Build filters
    start_date = None
    if days:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    history = db.get_usage_history(
        limit=limit,
        model_id=model,
        session_id=session,
        user_id=user,
        start_date=start_date
    )
    
    if json_output:
        console.print(json.dumps([usage.__dict__ for usage in history], indent=2))
        return
    
    if not history:
        console.print("[yellow]No token usage records found.[/yellow]")
        return
    
    # Create table
    table = Table(title="Token Usage History")
    table.add_column("Time", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Session", style="blue")
    table.add_column("Input", justify="right", style="yellow")
    table.add_column("Output", justify="right", style="yellow")
    table.add_column("Total", justify="right", style="bold")
    table.add_column("Cost", justify="right", style="red")
    
    for usage in history:
        table.add_row(
            usage.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            usage.model_id,
            usage.session_id[:8] + "..." if len(usage.session_id) > 8 else usage.session_id,
            str(usage.prompt_tokens),
            str(usage.completion_tokens),
            str(usage.total_tokens),
            f"${usage.cost_usd:.4f}"
        )
    
    console.print(table)


@tokens_app.command("summary")
def token_summary(
    period: str = typer.Option("day", "--period", "-p", help="Period: day, week, month, year"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Filter by model ID"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON")
) -> None:
    """Show token usage summary for a period."""
    
    db = get_token_database()
    
    try:
        summary = db.get_usage_summary(period=period, model_id=model, user_id=user)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    if json_output:
        console.print(json.dumps(summary, indent=2))
        return
    
    # Create summary panel
    total = summary["total"]
    
    panel_content = f"""
[bold]Period:[/bold] {period.title()} ({summary['start_date'][:10]} to {summary['end_date'][:10]})
[bold]Total Requests:[/bold] {total['requests']:,}
[bold]Total Tokens:[/bold] {total['total_tokens']:,}
  • Input: {total['prompt_tokens']:,}
  • Output: {total['completion_tokens']:,}
[bold]Total Cost:[/bold] ${total['cost_usd']:.4f}
[bold]Average Cost/1k Tokens:[/bold] ${(total['cost_usd'] / total['total_tokens'] * 1000) if total['total_tokens'] > 0 else 0:.4f}
    """
    
    console.print(Panel(panel_content.strip(), title="Token Usage Summary"))
    
    # Show breakdown by model if multiple models
    if len(summary["by_model"]) > 1:
        model_table = Table(title="Usage by Model")
        model_table.add_column("Model", style="green")
        model_table.add_column("Requests", justify="right")
        model_table.add_column("Tokens", justify="right")
        model_table.add_column("Cost", justify="right", style="red")
        
        for model_id, model_summary in summary["by_model"].items():
            model_table.add_row(
                model_id,
                str(model_summary["requests"]),
                str(model_summary["total_tokens"]),
                f"${model_summary['cost_usd']:.4f}"
            )
        
        console.print(model_table)


@tokens_app.command("costs")
def manage_costs(
    provider: str = typer.Option("local", "--provider", "-p", help="Provider name"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model ID (required unless using --list)"),
    input_cost: Optional[float] = typer.Option(None, "--input-cost", "-i", help="Input cost per 1k tokens"),
    output_cost: Optional[float] = typer.Option(None, "--output-cost", "-o", help="Output cost per 1k tokens"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all cost configurations"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove cost configuration")
) -> None:
    """Manage cost configurations."""
    
    db = get_token_database()
    
    if list_all:
        # List all cost configs
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT provider, model_id, input_cost_per_1k, output_cost_per_1k, currency, updated_at
                FROM cost_configs 
                ORDER BY provider, model_id
            """)
            
            configs = cursor.fetchall()
            
            if not configs:
                console.print("[yellow]No cost configurations found.[/yellow]")
                return
            
            table = Table(title="Cost Configurations")
            table.add_column("Provider", style="cyan")
            table.add_column("Model", style="green")
            table.add_column("Input/1k", justify="right", style="yellow")
            table.add_column("Output/1k", justify="right", style="yellow")
            table.add_column("Updated", style="blue")
            
            for config in configs:
                table.add_row(
                    config['provider'],
                    config['model_id'],
                    f"${config['input_cost_per_1k']:.4f}",
                    f"${config['output_cost_per_1k']:.4f}",
                    config['updated_at'][:19]
                )
            
            console.print(table)
            return
    
    if remove:
        # Remove cost config
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM cost_configs 
                WHERE provider = ? AND model_id = ?
            """, (provider, model))
            
            if cursor.rowcount > 0:
                console.print(f"[green]Removed cost config for {provider}/{model}[/green]")
                conn.commit()
            else:
                console.print(f"[yellow]No cost config found for {provider}/{model}[/yellow]")
        return
    
    if input_cost is not None and output_cost is not None:
        # Add/update cost config
        config = CostConfig(
            provider=provider,
            model_id=model,
            input_cost_per_1k=input_cost,
            output_cost_per_1k=output_cost
        )
        
        db.save_cost_config(config)
        console.print(f"[green]Saved cost config for {provider}/{model}[/green]")
        console.print(f"  Input: ${input_cost:.4f}/1k tokens")
        console.print(f"  Output: ${output_cost:.4f}/1k tokens")
    else:
        # Show current config
        existing = db.get_cost_config(provider, model)
        if existing:
            console.print(f"[bold]Current cost config for {provider}/{model}:[/bold]")
            console.print(f"  Input: ${existing.input_cost_per_1k:.4f}/1k tokens")
            console.print(f"  Output: ${existing.output_cost_per_1k:.4f}/1k tokens")
        else:
            console.print(f"[yellow]No cost config found for {provider}/{model}[/yellow]")
            console.print("Use --input-cost and --output-cost to set one.")


@tokens_app.command("export")
def export_usage(
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Export last N days")
) -> None:
    """Export token usage data."""
    
    db = get_token_database()
    
    # Build date range
    start_date = None
    if days:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Exporting usage data...", total=None)
        
        try:
            data = db.export_usage(format=format, start_date=start_date, end_date=datetime.now(timezone.utc))
            progress.update(task, description="Export complete!")
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")
            return
    
    # Save to file or print
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(data)
        
        console.print(f"[green]Exported to {output_path}[/green]")
    else:
        console.print(data)


@tokens_app.command("stats")
def token_stats(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Filter by model ID"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user ID"),
    days: int = typer.Option(30, "--days", "-d", help="Analysis period in days")
) -> None:
    """Show detailed usage statistics and analytics."""
    
    db = get_token_database()
    
    # Get data for the period
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    history = db.get_usage_history(
        limit=10000,  # Large limit for analytics
        start_date=start_date
    )
    
    if not history:
        console.print("[yellow]No usage data found for the specified period.[/yellow]")
        return
    
    # Apply filters
    if model:
        history = [h for h in history if h.model_id == model]
    if user:
        history = [h for h in history if h.user_id == user]
    
    if not history:
        console.print("[yellow]No usage data found after applying filters.[/yellow]")
        return
    
    # Calculate statistics
    total_requests = len(history)
    total_tokens = sum(h.total_tokens for h in history)
    total_cost = sum(h.cost_usd for h in history)
    
    # Daily averages
    avg_daily_requests = total_requests / days
    avg_daily_tokens = total_tokens / days
    avg_daily_cost = total_cost / days
    
    # Model breakdown
    model_stats = {}
    for usage in history:
        if usage.model_id not in model_stats:
            model_stats[usage.model_id] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0
            }
        model_stats[usage.model_id]["requests"] += 1
        model_stats[usage.model_id]["tokens"] += usage.total_tokens
        model_stats[usage.model_id]["cost"] += usage.cost_usd
    
    # Find most used model
    most_used_model = max(model_stats.items(), key=lambda x: x[1]["tokens"])
    
    # Create statistics panel
    stats_content = f"""
[bold]Analysis Period:[/bold] Last {days} days
[bold]Total Requests:[/bold] {total_requests:,} ({avg_daily_requests:.1f}/day)
[bold]Total Tokens:[/bold] {total_tokens:,} ({avg_daily_tokens:.0f}/day)
[bold]Total Cost:[/bold] ${total_cost:.4f} (${avg_daily_cost:.4f}/day)
[bold]Most Used Model:[/bold] {most_used_model[0]} ({most_used_model[1]['tokens']:,} tokens)
[bold]Average Cost/1k Tokens:[/bold] ${(total_cost / total_tokens * 1000) if total_tokens > 0 else 0:.4f}
    """
    
    console.print(Panel(stats_content.strip(), title="Usage Analytics"))
    
    # Model breakdown table
    model_table = Table(title="Model Breakdown")
    model_table.add_column("Model", style="green")
    model_table.add_column("Requests", justify="right")
    model_table.add_column("Tokens", justify="right")
    model_table.add_column("Cost", justify="right", style="red")
    model_table.add_column("% of Total", justify="right")
    
    for model_id, stats in sorted(model_stats.items(), key=lambda x: x[1]["tokens"], reverse=True):
        percentage = (stats["tokens"] / total_tokens) * 100
        model_table.add_row(
            model_id,
            str(stats["requests"]),
            str(stats["tokens"]),
            f"${stats['cost']:.4f}",
            f"{percentage:.1f}%"
        )
    
    console.print(model_table)


@tokens_app.command("reset")
def reset_tokens(
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Confirm reset operation"),
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Reset only last N days")
) -> None:
    """Reset token usage data (DANGEROUS!)."""
    
    if not confirm:
        console.print("[red]ERROR: This is a destructive operation![/red]")
        console.print("Use --confirm to proceed.")
        return
    
    db = get_token_database()
    
    with console.status("[bold red]Deleting token usage data...[/bold red]"):
        with sqlite3.connect(db.db_path) as conn:
            if days:
                start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                cursor = conn.execute("DELETE FROM token_usage WHERE timestamp >= ?", (start_date,))
                console.print(f"[green]Deleted {cursor.rowcount} records from last {days} days[/green]")
            else:
                cursor = conn.execute("DELETE FROM token_usage")
                console.print(f"[green]Deleted all {cursor.rowcount} token usage records[/green]")
            
            conn.commit()
    
    console.print("[yellow]Token usage data has been reset.[/yellow]")


# Add tokens app to main CLI
def register_tokens_app(main_app: typer.Typer):
    """Register tokens command group with main app."""
    main_app.add_typer(tokens_app, name="tokens")
