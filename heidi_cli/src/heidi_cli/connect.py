"""Connect module for external services."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def get_opencode_auth_path() -> Optional[Path]:
    """Get OpenCode auth.json path based on OS."""
    if os.name == "nt":
        # Windows
        user_profile = os.environ.get("USERPROFILE", "")
        return Path(user_profile) / ".local" / "share" / "opencode" / "auth.json"
    else:
        # macOS/Linux
        return Path.home() / ".local" / "share" / "opencode" / "auth.json"


def check_opencode_openai() -> tuple[bool, str]:
    """Check if OpenCode has OpenAI (ChatGPT Plus/Pro) auth.

    Returns (success, message).
    """
    opencode_path = shutil.which("opencode")
    if not opencode_path:
        return False, "OpenCode CLI not found. Install from https://opencode.ai"

    # Check if auth.json exists
    auth_path = get_opencode_auth_path()
    if not auth_path or not auth_path.exists():
        return False, "OpenCode auth not found. Run 'heidi connect opencode openai' to connect."

    # Check if npx is available for plugin install
    npx_path = shutil.which("npx")
    if not npx_path:
        return False, "npx not found. Install Node.js to use OpenAI provider."

    # Try to get OpenAI models
    try:
        result = subprocess.run(
            ["opencode", "models", "openai"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            model_count = len([line for line in lines if line.strip()])
            first_model = lines[0].strip() if lines else "unknown"
            return True, f"OpenAI connected: {model_count} models available (first: {first_model})"
        else:
            return False, "OpenAI not connected. Run 'heidi connect opencode openai' to connect."
    except Exception as e:
        return False, f"Error checking OpenAI models: {e}"


def connect_opencode_openai() -> tuple[bool, str]:
    """Connect OpenCode to OpenAI (ChatGPT Plus/Pro) via OAuth.

    Returns (success, message).
    """

    opencode_path = shutil.which("opencode")
    if not opencode_path:
        return False, "OpenCode CLI not found. Install from https://opencode.ai"

    npx_path = shutil.which("npx")
    if not npx_path:
        return False, "npx not found. Install Node.js to use OpenAI provider."

    # Install OpenCode OpenAI plugin (with output visible)
    print("Installing OpenCode OpenAI plugin...")
    print("  $ npx -y opencode-openai-codex-auth@latest")
    try:
        result = subprocess.run(
            ["npx", "-y", "opencode-openai-codex-auth@latest"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min for first install
        )
        if result.returncode != 0:
            if result.stderr:
                print(f"[red]Plugin install error: {result.stderr[:200]}[/red]")
            return False, "Plugin install failed"
    except subprocess.TimeoutExpired:
        return False, "Plugin install timed out (network issue?)"
    except Exception as e:
        return False, f"Plugin install error: {e}"

    print("")

    # Launch OpenCode login - run interactively so user sees prompts
    print("Launching OpenCode login...")
    print("  $ opencode auth login")
    print("")
    print("If browser doesn't open, the terminal will show a device code.")
    print("For headless: run 'codex login --device-auth' in another terminal.")
    print("")
    print("Waiting for login... (this may take a minute)")
    print("(Press Ctrl+C to cancel and try again)")
    print("")

    try:
        # Run without capture so user sees login flow
        result = subprocess.run(
            ["opencode", "auth", "login"],
            timeout=180,  # 3 min for OAuth
        )
        print("")
    except subprocess.TimeoutExpired:
        print("")
        print("[yellow]Login timed out. Checking if connection was established...[/yellow]")
    except KeyboardInterrupt:
        print("")
        return (
            False,
            "Login cancelled by user. Run 'heidi connect opencode openai --verify' to check.",
        )

    # Verify connection
    success, msg = check_opencode_openai()
    if success:
        return True, "Connected: OpenAI (ChatGPT Plus/Pro)"
    else:
        return False, "Connection not established. Try: codex login --device-auth"


def get_openai_models() -> list[str]:
    """Get list of available OpenAI models from OpenCode."""
    try:
        result = subprocess.run(
            ["opencode", "models", "openai"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            return [line.strip() for line in lines if line.strip()]
        return []
    except Exception:
        return []


def test_openai_connection() -> tuple[bool, str]:
    """Test OpenAI connection by running a simple command.

    Returns (success, message).
    """
    models = get_openai_models()
    if not models:
        return False, "No OpenAI models available"

    first_model = models[0]
    try:
        result = subprocess.run(
            ["opencode", "run", "say ok", f"--model=openai/{first_model.split('/')[-1]}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, f"Test run PASSED with model {first_model}"
        else:
            return False, f"Test run failed: {result.stderr[:200]}"
    except Exception as e:
        return False, f"Test run error: {e}"
