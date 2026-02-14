from __future__ import annotations

import httpx
import shutil
import subprocess
from typing import Optional

from rich.console import Console

console = Console()


def check_ollama(url: str, token: Optional[str] = None) -> tuple[bool, str]:
    """Check if Ollama is running and healthy.

    Returns (success, message) tuple.
    """
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = httpx.get(f"{url.rstrip('/')}/api/version", headers=headers, timeout=5)
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            return True, f"Ollama running (version: {version})"
        else:
            return False, f"Ollama returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused - is Ollama running?"
    except httpx.TimeoutException:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_opencode_cli() -> tuple[bool, str]:
    """Check if OpenCode CLI is installed.

    Returns (success, message) tuple.
    """
    result = shutil.which("opencode")
    if result:
        # Try to get version
        try:
            version_result = subprocess.run(
                ["opencode", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if version_result.returncode == 0:
                version = version_result.stdout.strip() or "unknown"
                return True, f"OpenCode CLI installed ({version})"
        except Exception:
            pass
        return True, "OpenCode CLI installed"
    return False, "OpenCode CLI not found in PATH"


def check_opencode_server(
    url: str, username: Optional[str] = None, password: Optional[str] = None
) -> tuple[bool, str]:
    """Check if OpenCode server is running.

    Returns (success, message) tuple.
    """
    try:
        auth = None
        if username and password:
            import base64

            auth = base64.b64encode(f"{username}:{password}".encode()).decode()

        headers = {}
        if auth:
            headers["Authorization"] = f"Basic {auth}"

        response = httpx.get(f"{url.rstrip('/')}/global/health", headers=headers, timeout=5)
        if response.status_code == 200:
            return True, "OpenCode server running"
        elif response.status_code == 401:
            return False, "Authentication required - check credentials"
        else:
            return False, f"Server returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused - is OpenCode server running?"
    except httpx.TimeoutException:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_heidi_backend(url: str) -> tuple[bool, str]:
    """Check if Heidi backend is running.

    Returns (success, message) tuple.
    """
    try:
        response = httpx.get(f"{url.rstrip('/')}/health", timeout=5)
        if response.status_code == 200:
            return True, "Heidi backend running"
        else:
            return False, f"Backend returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Backend not running"
    except httpx.TimeoutException:
        return False, "Backend connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"
