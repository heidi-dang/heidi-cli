"""ML fine-tuning helper commands.

Provides system probing, recommendations, and guidance for local ML workflows.
"""

from __future__ import annotations


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .system_probe import probe_and_recommend
from .cli import print_json

ml_app = typer.Typer(help="Local ML / fine-tuning helpers")
console = Console()


@ml_app.command()
def recommend(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    """Show ML fine-tuning recommendations based on system hardware.

    Detects GPU/RAM/OS/WSL and recommends optimal fine-tuning profiles
    with next-step commands. No network calls - all local probing.
    """
    if not json_output:
        console.print("[cyan]Probing system for ML capabilities...[/cyan]")

    try:
        data = probe_and_recommend()

        if json_output:
            print_json(data, ctx)
            return

        # Display summary table first
        system = data["system"]
        gpus = data["gpus"]
        caps = data["capabilities"]
        rec = data["recommendation"]

        # Summary table
        summary_table = Table(title="ML System Summary")
        summary_table.add_column("Component", style="cyan")
        summary_table.add_column("Details", style="white")

        # GPU summary
        if gpus:
            best_gpu = max(gpus, key=lambda g: g["memory_mb"])
            gpu_summary = (
                f"{best_gpu['vendor'].title()} {best_gpu['name']} ({best_gpu['memory_mb']} MB)"
            )
        else:
            gpu_summary = "No GPU detected"

        summary_table.add_row("OS", f"{system['os']} ({system['arch']})")
        if system["is_wsl"]:
            summary_table.add_row("Environment", f"WSL2 ({system.get('wsl_distro', 'Unknown')})")
        summary_table.add_row("GPU", gpu_summary)
        summary_table.add_row("RAM", f"{system['memory_gb']:.1f} GB")
        summary_table.add_row(
            "CUDA",
            "[green]Available[/green]" if caps["cuda_available"] else "[red]Not Available[/red]",
        )
        summary_table.add_row(
            "PyTorch",
            "[green]Installed[/green]" if caps["torch_installed"] else "[red]Not Installed[/red]",
        )
        summary_table.add_row(
            "Profile", f"[bold green]{rec['name'].replace('_', ' ').title()}[/bold green]"
        )

        console.print(summary_table)
        console.print()

        # Display system info
        table = Table(title="System Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("OS", f"{system['os']} ({system['arch']})")
        table.add_row("CPU Cores", str(system["cpu_count"]))
        table.add_row("Memory", f"{system['memory_gb']:.1f} GB")
        table.add_row("Free Disk", f"{system['disk_free_gb']:.1f} GB")
        table.add_row("Python", system["python_version"])
        if system["is_wsl"]:
            table.add_row("WSL", "[green]Yes[/green]")
            if system.get("wsl_distro"):
                table.add_row("WSL Distro", system["wsl_distro"])

        console.print(table)
        console.print()

        # Display GPU info
        if gpus:
            gpu_table = Table(title="GPU Information")
            gpu_table.add_column("GPU", style="cyan")
            gpu_table.add_column("Memory", style="white")
            gpu_table.add_column("Driver", style="dim")

            for i, gpu in enumerate(gpus, 1):
                memory_str = f"{gpu['memory_mb']} MB" if gpu["memory_mb"] > 0 else "Unknown"
                driver_str = gpu.get("driver_version", "Unknown")
                if gpu.get("cuda_version"):
                    driver_str += f" (CUDA {gpu['cuda_version']})"

                gpu_table.add_row(f"{gpu['vendor'].title()} {gpu['name']}", memory_str, driver_str)

            console.print(gpu_table)
        else:
            console.print("[yellow]No GPUs detected - CPU only[/yellow]")

        console.print()

        # Display capabilities
        caps_table = Table(title="ML Capabilities")
        caps_table.add_column("Capability", style="cyan")
        caps_table.add_column("Status", style="white")

        caps_table.add_row(
            "CUDA",
            "[green]Available[/green]" if caps["cuda_available"] else "[red]Not Available[/red]",
        )
        caps_table.add_row(
            "ROCm",
            "[green]Available[/green]" if caps["rocm_available"] else "[red]Not Available[/red]",
        )
        caps_table.add_row(
            "MLX",
            "[green]Available[/green]" if caps["mlx_available"] else "[red]Not Available[/red]",
        )
        caps_table.add_row(
            "PyTorch",
            "[green]Installed[/green]" if caps["torch_installed"] else "[red]Not Installed[/red]",
        )

        if caps.get("optimal_batch_size"):
            caps_table.add_row("Optimal Batch Size", str(caps["optimal_batch_size"]))

        console.print(caps_table)
        console.print()

        # Display recommendation
        rec_panel = Panel(
            f"[bold green]{rec['name'].replace('_', ' ').title()}[/bold green]\n\n"
            f"{rec['description']}\n\n"
            f"[dim]Recommended models:[/dim] {', '.join(rec['recommended_models'])}\n"
            f"[dim]Max sequence length:[/dim] {rec['max_sequence_length']}\n"
            f"[dim]Quantization:[/dim] {rec['quantization']}\n"
            f"[dim]Memory efficient:[/dim] {'Yes' if rec['memory_efficient'] else 'No'}",
            title="Recommended Profile",
            border_style="green",
        )
        console.print(rec_panel)

    except Exception as e:
        console.print(f"[red]Error during system probe: {e}[/red]")
        raise typer.Exit(1)


@ml_app.command()
def guide(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    """Show tailored setup guide based on system capabilities.

    Provides step-by-step instructions for setting up ML fine-tuning
    based on the detected hardware profile. No network calls.
    """
    if not json_output:
        console.print("[cyan]Analyzing system for setup guide...[/cyan]")

    try:
        data = probe_and_recommend()
        rec = data["recommendation"]
        system = data["system"]
        gpus = data["gpus"]
        caps = data["capabilities"]

        if json_output:
            # For JSON output, include the guide steps
            guide_data = {
                "profile": rec,
                "system": system,
                "gpus": gpus,
                "capabilities": caps,
                "guide_steps": rec["next_steps"],
            }
            print_json(guide_data, ctx)
            return

        # Display what you have
        console.print(
            Panel(
                f"[bold]Your System:[/bold]\n"
                f"OS: {system['os']} ({system['arch']})\n"
                f"RAM: {system['memory_gb']:.1f} GB\n"
                f"GPU: {gpus[0]['vendor'].title()} {gpus[0]['name']} ({gpus[0]['memory_mb']} MB)"
                if gpus
                else f"[bold]Your System:[/bold]\n"
                f"OS: {system['os']} ({system['arch']})\n"
                f"RAM: {system['memory_gb']:.1f} GB\n"
                f"GPU: CPU only",
                title="🔍 What You Have",
                border_style="blue",
            )
        )

        console.print()

        # Display recommendation
        console.print(
            Panel(
                f"[bold green]{rec['name'].replace('_', ' ').title()}[/bold green]\n"
                f"{rec['description']}",
                title="Recommended Profile",
                border_style="green",
            )
        )
        console.print()

        # Display setup steps
        console.print("[bold]Next Steps:[/bold]")
        console.print()

        for i, step in enumerate(rec["next_steps"], 1):
            console.print(f"[cyan]{i}.[/cyan] {step}")

        console.print()

        # Display quick start commands based on profile
        console.print("[bold]Quick Start Commands:[/bold]")
        console.print()

        if rec["name"].startswith("cpu"):
            console.print("# Install Ollama for easy model serving")
            console.print("curl -fsSL https://ollama.ai/install.sh | sh")
            console.print()
            console.print("# Pull a small model")
            console.print(f"ollama pull {rec['recommended_models'][0].replace('-instruct', '')}")
            console.print()
            console.print("# Start Ollama")
            console.print("ollama serve")

        elif rec["name"].startswith("nvidia"):
            console.print("# Install PyTorch with CUDA")
            console.print("pip install torch torchvision torchaudio")
            console.print()
            console.print("# Install training dependencies")
            console.print("pip install transformers accelerate")
            if rec["quantization"] == "4bit":
                console.print("pip install bitsandbytes peft")
            console.print()
            console.print("# Verify CUDA availability")
            console.print(
                "python -c \"import torch; print('CUDA available:', torch.cuda.is_available())\""
            )

        elif rec["name"].startswith("apple"):
            console.print("# Install MLX for Apple Silicon")
            console.print("pip install mlx mlx-lm")
            console.print()
            console.print("# Install transformers")
            console.print("pip install transformers")
            console.print()
            console.print("# Verify MLX availability")
            console.print("python -c \"import mlx.core; print('MLX available')\"")

        elif rec["name"].startswith("amd"):
            if caps["rocm_available"]:
                console.print("# Install PyTorch with ROCm")
                console.print("pip install torch --index-url https://download.pytorch.org/whl/rocm")
                console.print()
                console.print("# Install training dependencies")
                console.print("pip install transformers accelerate")
            else:
                console.print("# Install ROCm drivers for GPU acceleration")
                console.print("# See: https://rocm.docs.amd.com/en/latest/deploy/linux/index.html")
                console.print()
                console.print("# Or use CPU inference with Ollama")
                console.print("curl -fsSL https://ollama.ai/install.sh | sh")

        console.print()
        console.print("[dim]For detailed documentation: heidi docs local-ml.md[/dim]")

    except Exception as e:
        console.print(f"[red]Error generating guide: {e}[/red]")
        raise typer.Exit(1)
