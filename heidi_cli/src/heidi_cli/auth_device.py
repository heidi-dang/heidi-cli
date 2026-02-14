import asyncio
import os
import httpx
import time
from typing import Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


GITHUB_CLIENT_ID = os.getenv("HEIDI_GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("HEIDI_GITHUB_CLIENT_SECRET", "")


def get_client_id() -> str:
    """Get GitHub OAuth client ID."""
    if GITHUB_CLIENT_ID:
        return GITHUB_CLIENT_ID

    from .config import ConfigManager

    config = ConfigManager.load()
    return config.get("github_client_id", "")


async def request_device_code(
    client_id: str, scope: str = "read:user user:email copilot"
) -> Optional[Dict[str, Any]]:
    """Step A: Request a device code from GitHub."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/device/code",
            data={
                "client_id": client_id,
                "scope": scope,
            },
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        console.print(f"[red]Failed to request device code: {response.text}[/red]")
        return None

    return response.json()


async def poll_for_token(
    client_id: str, device_code: str, interval: int, timeout: int = 180
) -> Optional[Dict[str, Any]]:
    """Step B: Poll for the access token."""
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Waiting for authorization...", total=None)

        while time.time() - start_time < timeout:
            await asyncio.sleep(interval)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": client_id,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Accept": "application/json"},
                )

            if response.status_code != 200:
                continue

            data = response.json()

            if "access_token" in data:
                progress.update(task, description="[green]Authorization complete!")
                return data

            error = data.get("error", "")
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5
            elif error == "expired_token":
                progress.update(task, description="[red]Authorization timed out")
                return None
            elif error == "access_denied":
                console.print("[yellow]Authorization denied by user[/yellow]")
                return None
            else:
                console.print(f"[yellow]Error: {error}[/yellow]")
                return None

    console.print("[red]Authorization timed out[/red]")
    return None


async def complete_device_login(client_id: str) -> Optional[str]:
    """Complete the device flow login."""
    if not client_id:
        console.print("[red]No GitHub client ID configured.[/red]")
        console.print(
            "[dim]Set HEIDI_GITHUB_CLIENT_ID env var or configure via 'heidi config set github_client_id <id>'[/dim]"
        )
        return None

    console.print("[cyan]Requesting device code...[/cyan]")

    code_data = await request_device_code(client_id)
    if not code_data:
        return None

    device_code = code_data.get("device_code")
    user_code = code_data.get("user_code")
    verification_uri = code_data.get("verification_uri")
    interval = code_data.get("interval", 5)

    console.print(
        Panel.fit(
            f"[bold green]Code:[/bold green] {user_code}\n\n"
            f"Open: [link]{verification_uri}[/link]\n\n"
            f"[dim]Then enter the code above and approve access.[/dim]",
            title="GitHub Device Authorization",
        )
    )

    console.print("\n[cyan]Waiting for authorization... (press Ctrl+C to cancel)[/cyan]")

    token_data = await poll_for_token(client_id, device_code, interval)
    if not token_data:
        return None

    access_token = token_data.get("access_token")
    if not access_token:
        console.print("[red]No access token received[/red]")
        return None

    console.print("[green]Successfully authenticated![/green]")
    return access_token


def login_with_device_flow() -> Optional[str]:
    """Main entry point for device flow login."""
    client_id = get_client_id()

    if not client_id:
        console.print("[yellow]No GitHub OAuth client ID configured.[/yellow]")
        console.print("\nTo use device flow, you need to:")
        console.print("1. Create a GitHub OAuth App at: https://github.com/settings/developers")
        console.print("2. Set the client ID via:")
        console.print("   - Environment variable: HEIDI_GITHUB_CLIENT_ID")
        console.print("   - Or use: heidi config set github_client_id <id>")
        console.print("\nAlternatively, you can paste a GitHub PAT directly:")

        from .config import ConfigManager

        token = ConfigManager.get_github_token()
        if not token:
            console.print("\n[dim]No token configured yet.[/dim]")
        return None

    return asyncio.run(complete_device_login(client_id))
