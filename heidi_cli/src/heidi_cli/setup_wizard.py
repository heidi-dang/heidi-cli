from __future__ import annotations

import os
import shutil
import subprocess
import time

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import ConfigManager, check_legacy_heidi_dir, find_project_root, heidi_config_dir


console = Console()


class SetupWizard:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.openwebui_url = "http://localhost:3000"
        self.openwebui_token = None
        self.github_token = None
        self.project_root = find_project_root()
        self.legacy_heidi = check_legacy_heidi_dir()

    def run(self) -> None:
        """Run the complete setup wizard."""
        console.print(
            Panel.fit(
                "[bold cyan]Heidi CLI Setup Wizard[/bold cyan]\n\n"
                "This wizard will help you configure Heidi CLI for first use.",
                title="Welcome",
            )
        )

        # Step 1: Environment checks
        self._step1_environment_checks()

        # Step 2: Initialize project state
        self._step2_initialize_project()

        # Step 3: GitHub/Copilot setup
        self._step3_github_copilot_setup()

        # Step 4: OpenWebUI setup
        self._step4_openwebui_setup()

        # Step 5: Heidi server health check
        self._step5_server_health_check()

        # Step 6: OpenWebUI Tools connection guide
        self._step6_openwebui_guide()

        # Step 7: Final summary
        self._step7_final_summary()

    def _step1_environment_checks(self) -> None:
        """Step 1: Environment checks - Display checklist."""
        console.print("\n[bold]Step 1: Environment Checks[/bold]")

        table = Table(show_header=False)
        table.add_column("Item", style="cyan")
        table.add_column("Status", style="green")

        # Check Python
        python_ok = bool(shutil.which("python") or shutil.which("python3") or shutil.which("py"))
        table.add_row("Python", "✅ OK" if python_ok else "❌ Missing")

        # Check config dir (global)
        config_dir = heidi_config_dir()
        table.add_row(
            "Config dir (global)", "✅ Exists" if config_dir.exists() else "ℹ️  Will create"
        )

        # Check for legacy .heidi/
        if self.legacy_heidi:
            table.add_row("Legacy ./.heidi/", f"⚠️  Found at {self.legacy_heidi}")

        # Check tasks dir (project)
        tasks_dir = ConfigManager.tasks_dir()
        table.add_row(
            "Tasks dir (project)", "✅ Exists" if tasks_dir.exists() else "ℹ️  Will create"
        )

        # Heidi server base
        table.add_row("Heidi server base: http://localhost:7777", "ℹ️  Ready")

        console.print(table)

    def _step2_initialize_project(self) -> None:
        """Step 2: Initialize config and state directories."""
        console.print("\n[bold]Step 2: Initialize Heidi Configuration[/bold]")

        # Check for legacy .heidi/ and warn
        if self.legacy_heidi:
            console.print(f"\n[yellow]Found legacy .heidi/ at {self.legacy_heidi}[/yellow]")
            console.print(f"[dim]New default is {heidi_config_dir()}[/dim]")
            console.print("[dim]Run 'heidi migrate' later to move config if desired.[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating configuration directories...", total=None)

            # Create global config directory
            ConfigManager.ensure_dirs()

            # Ensure secrets file permissions 0600
            secrets_file = ConfigManager.secrets_file()
            if secrets_file.exists():
                secrets_file.chmod(0o600)

            progress.update(task, description="Ensuring tasks dir exists...")

            # Create tasks dir in project
            tasks_dir = ConfigManager.tasks_dir()
            tasks_dir.mkdir(parents=True, exist_ok=True)

            progress.update(task, description="Configuration initialized!")

        console.print("✅ Project state initialized")

    def _step3_github_copilot_setup(self) -> None:
        """Step 3: GitHub/Copilot setup - Configure GitHub token and test."""
        console.print("\n[bold]Step 3: GitHub/Copilot Setup[/bold]")

        if not Confirm.ask("Configure GitHub token now?", default=True):
            console.print("ℹ️  Skipping GitHub configuration")
            return

        console.print(
            "\n[dim]For Copilot, use a fine-grained token (github_pat_...) with 'Copilot' permission.[/dim]"
        )
        console.print("[dim]Create at: https://github.com/settings/tokens/new?scopes=copilot[/dim]")

        token = Prompt.ask("Enter GitHub fine-grained token (github_pat_...)", password=True)

        if not token:
            console.print("⚠️  No token provided, skipping GitHub configuration")
            return

        if token.startswith("ghp_"):
            console.print("\n[yellow]Warning: You entered a classic token (ghp_...).[/yellow]")
            console.print(
                "[yellow]Copilot often requires fine-grained tokens (github_pat_...).[/yellow]"
            )
            if not Confirm.ask("Continue anyway?", default=False):
                return

        self.github_token = token
        ConfigManager.set_github_token(token, store_keyring=True)
        console.print("✅ GitHub token stored successfully")

        # Test GitHub auth (must not show token)
        console.print("\nTesting GitHub authentication...")
        try:
            result = subprocess.run(
                ["heidi", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "HEIDI_NO_WIZARD": "1"},
            )
            if result.returncode == 0:
                console.print("✅ heidi auth status: PASS")
            else:
                console.print("❌ heidi auth status: FAIL")
        except subprocess.TimeoutExpired:
            console.print("⚠️  heidi auth status: TIMEOUT")
        except Exception:
            console.print("❌ heidi auth status: FAIL")

        # Test Copilot status first
        console.print("\nRunning Copilot status...")
        copilot_status_output = ""
        try:
            result = subprocess.run(
                ["heidi", "copilot", "status"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "HEIDI_NO_WIZARD": "1"},
            )
            copilot_status_output = result.stdout + result.stderr
            if result.returncode == 0 and "isAuthenticated=True" in copilot_status_output:
                console.print("✅ heidi copilot status: PASS")
            else:
                console.print("⚠️  heidi copilot status: FAIL")
        except subprocess.TimeoutExpired:
            console.print("⚠️  heidi copilot status: TIMEOUT")
        except Exception as e:
            console.print(f"⚠️  heidi copilot status: ERROR - {e}")

        # Test Copilot doctor
        console.print("\nRunning Copilot doctor...")
        try:
            result = subprocess.run(
                ["heidi", "copilot", "doctor"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "HEIDI_NO_WIZARD": "1"},
            )
            output = result.stdout + result.stderr

            if result.returncode == 0:
                console.print("✅ heidi copilot doctor: PASS")
            elif (
                "needs token" in output.lower()
                or "unauthorized" in output.lower()
                or "permission" in output.lower()
            ):
                console.print("⚠️  heidi copilot doctor: FAIL (token lacks Copilot permission)")
                console.print("[dim]Your token may need 'Copilot' permission.[/dim]")
                console.print(
                    "[dim]Create at: https://github.com/settings/tokens/new?scopes=copilot[/dim]"
                )
            else:
                console.print("⚠️  heidi copilot doctor: FAIL")
                if output.strip():
                    for line in output.strip().split("\n")[-5:]:
                        console.print(f"  [dim]{line}[/dim]")
        except subprocess.TimeoutExpired:
            console.print("⚠️  heidi copilot doctor: TIMEOUT")
        except Exception as e:
            console.print(f"⚠️  heidi copilot doctor: ERROR - {e}")

        # Optionally test chat
        if Confirm.ask("Test Copilot chat with 'hello'?", default=False):
            console.print("\nTesting Copilot chat...")
            try:
                result = subprocess.run(
                    ["heidi", "copilot", "chat", "hello"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    console.print("✅ Copilot chat: PASS")
                else:
                    console.print("❌ Copilot chat: FAIL")
            except subprocess.TimeoutExpired:
                console.print("⚠️  Copilot chat: TIMEOUT")
            except Exception:
                console.print("❌ Copilot chat: FAIL")

    def _step4_openwebui_setup(self) -> None:
        """Step 4: OpenWebUI setup - Configure URL and API key, then test."""
        console.print("\n[bold]Step 4: OpenWebUI Setup[/bold]")

        # Get OpenWebUI URL
        self.openwebui_url = Prompt.ask("OpenWebUI URL", default="http://localhost:3000")

        # Get OpenWebUI API key (hidden; allow skip)
        token = Prompt.ask(
            "OpenWebUI API key (optional, but recommended)", password=True, default=""
        )

        if token:
            self.openwebui_token = token
            # Save to config
            self.config.openwebui_url = self.openwebui_url
            self.config.openwebui_token = self.openwebui_token
            ConfigManager.save_config(self.config)

        # Status check - call OpenWebUI API endpoint
        console.print("\nTesting OpenWebUI connection...")
        success, message = self._test_openwebui_connection()

        if success:
            console.print(f"[green]✅ {message}[/green]")
        else:
            console.print(f"[red]❌ {message}[/red]")

            # Provide specific hints based on error
            if "connection refused" in message.lower():
                console.print("[yellow]💡 Hint: OpenWebUI is not running. Start it first.[/yellow]")
            elif "401" in message or "unauthorized" in message.lower():
                console.print(
                    "[yellow]💡 Hint: Invalid token. Check your API key in OpenWebUI Settings > Account.[/yellow]"
                )

    def _step5_server_health_check(self) -> None:
        """Step 5: Heidi server health check - Start server and verify /health."""
        console.print("\n[bold]Step 5: Heidi Server Health Check[/bold]")

        # Check if server is already running
        try:
            response = httpx.get("http://localhost:7777/health", timeout=5)
            if response.status_code == 200:
                console.print("✅ Heidi server is already running")
                return
        except Exception:
            pass

        # Ask to start server
        if not Confirm.ask("Start Heidi server now?", default=True):
            console.print("ℹ️  Skipping server start")
            return

        console.print("Starting Heidi server...")

        # Start server in background
        try:
            # Use subprocess.Popen to start server in background
            _server_process = subprocess.Popen(
                ["heidi", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Wait a bit for server to start
            time.sleep(3)

            # Test health endpoint
            try:
                response = httpx.get("http://localhost:7777/health", timeout=5)
                if response.status_code == 200:
                    console.print("✅ Heidi server started and healthy")
                else:
                    console.print(
                        f"❌ Heidi server health check failed: HTTP {response.status_code}"
                    )
            except Exception as e:
                console.print(f"❌ Heidi server health check failed: {e}")

        except Exception as e:
            console.print(f"❌ Failed to start Heidi server: {e}")

    def _step6_openwebui_guide(self) -> None:
        """Step 6: OpenWebUI Tools connection guide - Print exact URLs."""
        console.print("\n[bold]Step 6: OpenWebUI Tools Connection Guide[/bold]")

        console.print(
            Panel.fit(
                "To connect Heidi CLI as OpenAPI tools in OpenWebUI:\n\n"
                "1. Open OpenWebUI in your browser\n"
                "2. Go to: Settings → Connections → OpenAPI Servers\n"
                "3. Click 'Add Server' and configure:\n"
                "   • Name: Heidi CLI\n"
                "   • OpenAPI Spec URL: http://localhost:7777/openapi.json\n"
                "4. Save and test the connection",
                title="OpenWebUI Configuration",
            )
        )

        console.print("\n[bold]Quick Test URLs:[/bold]")
        console.print("• Health: http://localhost:7777/health")
        console.print("• Agents: http://localhost:7777/agents")
        console.print("• Runs: http://localhost:7777/runs")
        console.print("• Stream: http://localhost:7777/runs/<id>/stream (SSE)")

    def _step7_final_summary(self) -> None:
        """Step 7: Final summary - Print table with all status checks."""
        console.print("\n[bold]Step 7: Final Summary[/bold]")

        table = Table(title="Heidi CLI Setup Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        # Check each component
        initialized = ConfigManager.config_file().exists()
        table.add_row("Initialized project state", "✅" if initialized else "❌")

        github_configured = bool(self.github_token or ConfigManager.get_github_token())
        table.add_row("GitHub token configured", "✅" if github_configured else "⚠️")

        # Copilot doctor status
        copilot_ok = False
        try:
            result = subprocess.run(["heidi", "copilot", "doctor"], capture_output=True, timeout=10)
            copilot_ok = result.returncode == 0
        except Exception:
            pass
        table.add_row("Copilot doctor", "✅" if copilot_ok else "❌")

        # OpenWebUI reachable
        openwebui_ok = False
        try:
            if self.openwebui_token:
                headers = {"Authorization": f"Bearer {self.openwebui_token}"}
                response = httpx.get(f"{self.openwebui_url}/api/models", headers=headers, timeout=5)
                openwebui_ok = response.status_code == 200
            else:
                response = httpx.get(self.openwebui_url, timeout=5)
                openwebui_ok = response.status_code < 500
        except Exception:
            pass
        table.add_row("OpenWebUI reachable", "✅" if openwebui_ok else "⚠️")

        # Heidi server reachable
        server_ok = False
        try:
            response = httpx.get("http://localhost:7777/health", timeout=5)
            server_ok = response.status_code == 200
        except Exception:
            pass
        table.add_row("Heidi server reachable", "✅" if server_ok else "⚠️")

        table.add_row("OpenWebUI tools URL shown", "✅")

        console.print(table)

        console.print(
            Panel.fit(
                "🎉 Setup complete! You can now use Heidi CLI.\n\n"
                "Next steps:\n"
                "• Run 'heidi --help' for all commands\n"
                "• Use 'heidi serve' to start the server\n"
                "• Configure OpenWebUI with the provided settings",
                title="Setup Complete",
            )
        )

    def _test_openwebui_connection(self) -> tuple[bool, str]:
        """Test OpenWebUI connection and return (success, message)."""
        try:
            headers = {}
            if self.openwebui_token:
                headers["Authorization"] = f"Bearer {self.openwebui_token}"

            # Test the /api/models endpoint as documented
            response = httpx.get(f"{self.openwebui_url}/api/models", headers=headers, timeout=10)

            if response.status_code == 200:
                return True, "OpenWebUI API: OK"
            elif response.status_code == 401:
                return False, "OpenWebUI API: Token invalid (401)"
            else:
                return False, f"OpenWebUI API: HTTP {response.status_code}"
        except httpx.ConnectError:
            return False, "OpenWebUI API: Connection refused (not running?)"
        except Exception as e:
            return False, f"OpenWebUI API: Error - {e}"
