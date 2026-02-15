from __future__ import annotations

import re
import shutil
import subprocess
from typing import Optional, Tuple

from rich.console import Console

console = Console()


def is_cloudflared_installed() -> bool:
    """Check if cloudflared is installed."""
    return shutil.which("cloudflared") is not None


def start_tunnel(local_url: str) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """
    Start a Cloudflare tunnel to the local URL.

    Returns (process, public_url) tuple. public_url is None if tunnel fails.
    """
    if not is_cloudflared_installed():
        console.print("[yellow]cloudflared not found. Installing...[/yellow]")
        console.print(
            "[dim]Visit https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/ to install cloudflared[/dim]"
        )
        return None, None

    console.print(f"[cyan]Starting Cloudflare tunnel to {local_url}...[/cyan]")

    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", local_url, "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    public_url = None

    try:
        import time

        start_time = time.time()
        timeout = 30

        while time.time() - start_time < timeout:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue

            console.print(f"[dim]cloudflared: {line.rstrip()}[/dim]")

            # Parse the URL from cloudflared output
            match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
            if match:
                public_url = match.group(0)
                break

            match = re.search(r"https://[^\s]+", line)
            if match:
                public_url = match.group(0)
                break

        if public_url:
            console.print(f"[green]Tunnel ready: {public_url}[/green]")
        else:
            console.print("[yellow]Could not parse tunnel URL[/yellow]")

    except Exception as e:
        console.print(f"[red]Error starting tunnel: {e}[/red]")

    return process, public_url


def stop_tunnel(process: Optional[subprocess.Popen]) -> None:
    """Stop the tunnel process gracefully."""
    if process is None:
        return

    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    except Exception as e:
        console.print(f"[yellow]Warning: Error stopping tunnel: {e}[/yellow]")


def get_tunnel_instructions() -> str:
    """Get instructions for installing cloudflared."""
    return """To use Cloudflare Tunnel, install cloudflared:

# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Windows
Download from https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
"""
