"""System probing for ML fine-tuning recommendations.

Detects GPU/RAM/OS/WSL and provides hardware capability assessment
for local ML fine-tuning workflows.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class GPUVendor(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    INTEL = "intel"
    UNKNOWN = "unknown"


@dataclass
class GPUInfo:
    """GPU information for ML capability assessment."""

    vendor: GPUVendor
    name: str
    memory_mb: int
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None
    rocm_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor": self.vendor.value,
            "name": self.name,
            "memory_mb": self.memory_mb,
            "driver_version": self.driver_version,
            "cuda_version": self.cuda_version,
            "rocm_version": self.rocm_version,
        }


@dataclass
class SystemInfo:
    """System information for ML capability assessment."""

    os: str
    arch: str
    python_version: str
    cpu_count: int
    memory_gb: float
    disk_free_gb: float
    is_wsl: bool = False
    wsl_distro: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os": self.os,
            "arch": self.arch,
            "cpu_count": self.cpu_count,
            "memory_gb": round(self.memory_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
            "is_wsl": self.is_wsl,
            "wsl_distro": self.wsl_distro,
            "python_version": self.python_version,
        }


@dataclass
class MLCapabilities:
    """ML framework and hardware capabilities."""

    cuda_available: bool = False
    rocm_available: bool = False
    mlx_available: bool = False
    torch_installed: bool = False
    optimal_batch_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cuda_available": self.cuda_available,
            "rocm_available": self.rocm_available,
            "mlx_available": self.mlx_available,
            "torch_installed": self.torch_installed,
            "optimal_batch_size": self.optimal_batch_size,
        }


@dataclass
class MLProfile:
    """ML fine-tuning profile recommendation."""

    name: str
    description: str
    recommended_models: List[str]
    max_sequence_length: int
    quantization: str
    memory_efficient: bool
    next_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "recommended_models": self.recommended_models,
            "max_sequence_length": self.max_sequence_length,
            "quantization": self.quantization,
            "memory_efficient": self.memory_efficient,
            "next_steps": self.next_steps,
        }


def _run_command(cmd: List[str], timeout: int = 5) -> tuple[bool, str]:
    """Run command with timeout, never raise on non-zero exit."""
    try:
        # Windows-specific: avoid creating new console window
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
            creationflags=creation_flags,
        )
        # Truncate output to prevent excessive data
        output = result.stdout.strip()
        if len(output) > 2048:  # 2KB limit
            output = output[:2048] + "... [truncated]"
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
        return False, ""


def probe_system() -> SystemInfo:
    """Probe basic system information."""
    # OS and architecture
    os_name = platform.system().lower()
    arch = platform.machine().lower()

    # WSL detection
    is_wsl = False
    wsl_distro = None
    if os_name == "linux":
        # Check for WSL indicators
        wsl_indicators = [
            "/proc/version",
            "/proc/sys/kernel/osrelease",
        ]
        for indicator in wsl_indicators:
            try:
                with open(indicator, "r") as f:
                    content = f.read().lower()
                    if "microsoft" in content or "wsl" in content:
                        is_wsl = True
                        # Try to get distro name
                        if indicator == "/proc/version":
                            # Extract distro from version string like "Microsoft WSL 2 Ubuntu-20.04"
                            if "ubuntu" in content:
                                wsl_distro = "Ubuntu"
                            elif "debian" in content:
                                wsl_distro = "Debian"
                            elif "fedora" in content:
                                wsl_distro = "Fedora"
                            elif "opensuse" in content:
                                wsl_distro = "openSUSE"
                            else:
                                wsl_distro = "Unknown"
                        break
            except (FileNotFoundError, PermissionError):
                continue

    # CPU count
    cpu_count = os.cpu_count() or 0

    # Memory
    memory_gb = 0.0
    if PSUTIL_AVAILABLE:
        try:
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
        except Exception:
            pass

    # Disk space (current directory)
    disk_free_gb = 0.0
    try:
        stat = Path.cwd().statvfs()
        disk_free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
    except (AttributeError, OSError):
        # Windows fallback
        try:
            import shutil

            disk_usage = shutil.disk_usage(Path.cwd())
            disk_free_gb = disk_usage.free / (1024**3)
        except Exception:
            pass

    # Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return SystemInfo(
        os=os_name,
        arch=arch,
        cpu_count=cpu_count,
        memory_gb=memory_gb,
        disk_free_gb=disk_free_gb,
        is_wsl=is_wsl,
        wsl_distro=wsl_distro,
        python_version=python_version,
    )


def probe_nvidia_gpus() -> List[GPUInfo]:
    """Probe NVIDIA GPUs using nvidia-smi."""
    success, output = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version,cuda_version",
            "--format=csv,noheader,nounits",
        ],
        timeout=3,
    )

    if not success:
        return []

    gpus = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Allowlist parsing - only extract expected fields
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 4:
            # Sanitize GPU name to remove any potential sensitive info
            name = parts[0][:100]  # Limit length
            memory_mb = 0
            try:
                memory_mb = int(parts[1]) if parts[1].isdigit() else 0
            except ValueError:
                memory_mb = 0

            driver_version = parts[2][:20] if parts[2] else None  # Limit length
            cuda_version = parts[3][:20] if parts[3] else None  # Limit length

            gpus.append(
                GPUInfo(
                    vendor=GPUVendor.NVIDIA,
                    name=name,
                    memory_mb=memory_mb,
                    driver_version=driver_version,
                    cuda_version=cuda_version,
                )
            )

    return gpus


def probe_amd_gpus() -> List[GPUInfo]:
    """Probe AMD GPUs using amd-smi or rocm-smi."""
    gpus = []

    # Try amd-smi first (modern replacement)
    success, output = _run_command(["amd-smi", "--showproductname"])
    if success:
        # Parse amd-smi output
        lines = output.split("\n")
        for line in lines:
            if "GPU" in line and "Series" in line:
                # This is a simplified parser - real implementation would be more robust
                name = line.split(":", 1)[-1].strip()
                gpus.append(
                    GPUInfo(
                        vendor=GPUVendor.AMD,
                        name=name,
                        memory_mb=0,  # Would need additional commands to get memory
                    )
                )

    # Fallback to rocm-smi
    if not gpus:
        success, output = _run_command(["rocm-smi", "--showproductname"])
        if success:
            # Parse rocm-smi output similar to amd-smi
            lines = output.split("\n")
            for line in lines:
                if "GPU" in line and "Series" in line:
                    name = line.split(":", 1)[-1].strip()
                    gpus.append(
                        GPUInfo(
                            vendor=GPUVendor.AMD,
                            name=name,
                            memory_mb=0,
                        )
                    )

    return gpus


def probe_windows_gpus() -> List[GPUInfo]:
    """Probe GPUs on Windows using PowerShell."""
    success, output = _run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json",
        ]
    )

    if not success:
        return []

    gpus = []
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]  # Single GPU case

        for gpu_data in data:
            name = gpu_data.get("Name", "Unknown")
            adapter_ram = gpu_data.get("AdapterRAM", 0)
            memory_mb = int(adapter_ram / (1024 * 1024)) if adapter_ram else 0

            # Determine vendor from name
            vendor = GPUVendor.UNKNOWN
            name_lower = name.lower()
            if (
                "nvidia" in name_lower
                or "geforce" in name_lower
                or "quadro" in name_lower
                or "tesla" in name_lower
            ):
                vendor = GPUVendor.NVIDIA
            elif "amd" in name_lower or "radeon" in name_lower:
                vendor = GPUVendor.AMD
            elif "intel" in name_lower:
                vendor = GPUVendor.INTEL

            gpus.append(
                GPUInfo(
                    vendor=vendor,
                    name=name,
                    memory_mb=memory_mb,
                )
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return gpus


def probe_mac_gpus() -> List[GPUInfo]:
    """Probe GPUs on macOS using system_profiler."""
    success, output = _run_command(["system_profiler", "SPDisplaysDataType"])

    if not success:
        return []

    gpus = []
    current_gpu = {}

    for line in output.split("\n"):
        line = line.strip()

        if line.startswith("Chipset Model:"):
            if current_gpu:
                # Save previous GPU
                gpus.append(
                    GPUInfo(
                        vendor=current_gpu.get("vendor", GPUVendor.UNKNOWN),
                        name=current_gpu.get("name", "Unknown"),
                        memory_mb=current_gpu.get("memory_mb", 0),
                    )
                )

            # Start new GPU
            name = line.split(":", 1)[-1].strip()
            vendor = GPUVendor.UNKNOWN
            memory_mb = 0

            name_lower = name.lower()
            if (
                "apple" in name_lower
                or "m1" in name_lower
                or "m2" in name_lower
                or "m3" in name_lower
            ):
                vendor = GPUVendor.APPLE
            elif "amd" in name_lower or "radeon" in name_lower:
                vendor = GPUVendor.AMD
            elif "intel" in name_lower:
                vendor = GPUVendor.INTEL

            current_gpu = {"name": name, "vendor": vendor, "memory_mb": memory_mb}

        elif line.startswith("VRAM (Dynamic):"):
            try:
                vram_str = line.split(":", 1)[-1].strip()
                # Parse "VRAM (Dynamic): 8 GB"
                if "GB" in vram_str:
                    memory_gb = float(vram_str.split("GB")[0].strip())
                    memory_mb = int(memory_gb * 1024)
                    current_gpu["memory_mb"] = memory_mb
            except (ValueError, IndexError):
                pass

    # Add last GPU
    if current_gpu:
        gpus.append(
            GPUInfo(
                vendor=current_gpu.get("vendor", GPUVendor.UNKNOWN),
                name=current_gpu.get("name", "Unknown"),
                memory_mb=current_gpu.get("memory_mb", 0),
            )
        )

    return gpus


def probe_gpus() -> List[GPUInfo]:
    """Probe GPUs based on platform."""
    system = probe_system()

    if system.os == "windows":
        return probe_windows_gpus()
    elif system.os == "darwin":  # macOS
        return probe_mac_gpus()
    elif system.os == "linux":
        # Try NVIDIA first, then AMD
        gpus = probe_nvidia_gpus()
        if not gpus:
            gpus = probe_amd_gpus()
        return gpus

    return []


def check_ml_capabilities(system: SystemInfo, gpus: List[GPUInfo]) -> MLCapabilities:
    """Check ML framework and hardware capabilities."""
    capabilities = MLCapabilities()

    # Check CUDA availability (NVIDIA GPUs)
    nvidia_gpus = [gpu for gpu in gpus if gpu.vendor == GPUVendor.NVIDIA]
    if nvidia_gpus:
        capabilities.cuda_available = True

    # Check ROCm availability (AMD GPUs)
    amd_gpus = [gpu for gpu in gpus if gpu.vendor == GPUVendor.AMD]
    if amd_gpus:
        # Check if ROCm is actually available
        success, _ = _run_command(["rocminfo"], timeout=3)
        capabilities.rocm_available = success

    # Check MLX availability (Apple Silicon)
    if system.os == "darwin" and system.arch in ("arm64", "aarch64"):
        apple_gpus = [gpu for gpu in gpus if gpu.vendor == GPUVendor.APPLE]
        if apple_gpus:
            # Check if MLX is installed
            capabilities.mlx_available = importlib.util.find_spec("mlx.core") is not None

    # Check PyTorch installation
    try:
        import torch

        capabilities.torch_installed = True

        # Check if CUDA is available in PyTorch
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            # Estimate optimal batch size based on GPU memory
            if nvidia_gpus:
                max_memory_mb = max(gpu.memory_mb for gpu in nvidia_gpus)
                # Rough heuristic: 1GB memory can handle batch size 1-2 for 7B models
                capabilities.optimal_batch_size = max(1, min(8, max_memory_mb // 1024))
    except ImportError:
        pass

    return capabilities


def recommend_profile(
    system: SystemInfo, gpus: List[GPUInfo], capabilities: MLCapabilities
) -> MLProfile:
    """Recommend ML fine-tuning profile based on hardware capabilities."""

    # Sort GPUs by memory
    gpus_by_memory = sorted(gpus, key=lambda g: g.memory_mb, reverse=True)
    best_gpu = gpus_by_memory[0] if gpus_by_memory else None

    # Determine profile based on hardware
    if not best_gpu or best_gpu.memory_mb == 0:
        # CPU-only or unknown GPU
        return MLProfile(
            name="cpu_rag_only",
            description="CPU-only system suitable for RAG and inference",
            recommended_models=["llama3.2-1b", "phi3-mini", "qwen2-0.5b"],
            max_sequence_length=2048,
            quantization="4bit",
            memory_efficient=True,
            next_steps=[
                "Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh",
                "Pull a small model: ollama pull llama3.2:1b",
                "Run RAG setup: heidi ml guide",
            ],
        )

    # NVIDIA GPU profiles
    if best_gpu.vendor == GPUVendor.NVIDIA:
        if best_gpu.memory_mb >= 24000:  # 24GB+
            return MLProfile(
                name="nvidia_24gb_full_finetune",
                description="High-end NVIDIA GPU suitable for full fine-tuning",
                recommended_models=["llama3.1-8b", "mistral-7b", "qwen2-7b"],
                max_sequence_length=8192,
                quantization="16bit",
                memory_efficient=False,
                next_steps=[
                    "Install PyTorch with CUDA: pip install torch torchvision torchaudio",
                    "Install transformers: pip install transformers accelerate",
                    "Start fine-tuning: heidi ml guide",
                ],
            )
        elif best_gpu.memory_mb >= 8000:  # 8GB+
            return MLProfile(
                name="nvidia_8gb_qlora",
                description="Mid-range NVIDIA GPU suitable for QLoRA fine-tuning",
                recommended_models=["llama3.2-3b", "phi3-mini", "qwen2-1.5b"],
                max_sequence_length=4096,
                quantization="4bit",
                memory_efficient=True,
                next_steps=[
                    "Install PyTorch with CUDA: pip install torch torchvision torchaudio",
                    "Install bitsandbytes: pip install bitsandbytes",
                    "Start QLoRA training: heidi ml guide",
                ],
            )
        elif best_gpu.memory_mb >= 4000:  # 4GB+
            return MLProfile(
                name="nvidia_4gb_inference",
                description="Entry-level NVIDIA GPU suitable for inference and small model training",
                recommended_models=["llama3.2-1b", "phi3-mini", "qwen2-0.5b"],
                max_sequence_length=2048,
                quantization="4bit",
                memory_efficient=True,
                next_steps=[
                    "Install PyTorch with CUDA: pip install torch torchvision torchaudio",
                    "Use quantized models: heidi ml guide",
                ],
            )

    # Apple Silicon profiles
    elif best_gpu.vendor == GPUVendor.APPLE:
        if best_gpu.memory_mb >= 16000:  # 16GB+ unified memory
            return MLProfile(
                name="apple_silicon_16gb_mlx",
                description="Apple Silicon with MLX acceleration",
                recommended_models=["llama3.2-3b", "phi3-mini", "qwen2-1.5b"],
                max_sequence_length=4096,
                quantization="8bit",
                memory_efficient=True,
                next_steps=[
                    "Install MLX: pip install mlx mlx-lm",
                    "Install transformers: pip install transformers",
                    "Start MLX training: heidi ml guide",
                ],
            )
        else:  # 8GB unified memory
            return MLProfile(
                name="apple_silicon_8gb_mlx",
                description="Apple Silicon with MLX acceleration (memory constrained)",
                recommended_models=["llama3.2-1b", "phi3-mini", "qwen2-0.5b"],
                max_sequence_length=2048,
                quantization="4bit",
                memory_efficient=True,
                next_steps=[
                    "Install MLX: pip install mlx mlx-lm",
                    "Use small models: heidi ml guide",
                ],
            )

    # AMD GPU profiles
    elif best_gpu.vendor == GPUVendor.AMD:
        if capabilities.rocm_available:
            return MLProfile(
                name="amd_rocm_qlora",
                description="AMD GPU with ROCm support for QLoRA training",
                recommended_models=["llama3.2-3b", "phi3-mini", "qwen2-1.5b"],
                max_sequence_length=4096,
                quantization="4bit",
                memory_efficient=True,
                next_steps=[
                    "Install PyTorch with ROCm: pip install torch --index-url https://download.pytorch.org/whl/rocm",
                    "Install ROCm packages if needed",
                    "Start training: heidi ml guide",
                ],
            )
        else:
            return MLProfile(
                name="amd_inference_only",
                description="AMD GPU without ROCm, inference only",
                recommended_models=["llama3.2-1b", "phi3-mini", "qwen2-0.5b"],
                max_sequence_length=2048,
                quantization="4bit",
                memory_efficient=True,
                next_steps=[
                    "Use CPU inference or install ROCm drivers",
                    "Consider Ollama for easy model serving",
                ],
            )

    # Default fallback
    return MLProfile(
        name="generic_inference",
        description="Generic system suitable for inference",
        recommended_models=["llama3.2-1b", "phi3-mini"],
        max_sequence_length=2048,
        quantization="4bit",
        memory_efficient=True,
        next_steps=[
            "Install Ollama for easy model serving",
            "Use pre-trained models via heidi ml guide",
        ],
    )


def probe_and_recommend() -> Dict[str, Any]:
    """Full system probe and recommendation pipeline."""
    errors = []

    try:
        system = probe_system()
    except Exception as e:
        # Fallback system info if probing fails
        system = SystemInfo(
            os=platform.system().lower(),
            arch=platform.machine().lower(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            cpu_count=1,
            memory_gb=1.0,
            disk_free_gb=1.0,
            is_wsl=False,
            wsl_distro=None,
        )
        errors.append(f"System probe failed: {e}")

    try:
        gpus = probe_gpus()
    except Exception as e:
        gpus = []
        errors.append(f"GPU probe failed: {e}")

    try:
        capabilities = check_ml_capabilities(system, gpus)
    except Exception as e:
        capabilities = MLCapabilities()
        errors.append(f"Capability check failed: {e}")

    try:
        profile = recommend_profile(system, gpus, capabilities)
    except Exception as e:
        # Fallback CPU-only profile
        profile = MLProfile(
            name="cpu_only_inference",
            description="CPU-only inference (fallback)",
            recommended_models=["llama3.2-1b"],
            max_sequence_length=512,
            quantization="4bit",
            memory_efficient=True,
            next_steps=["Install Ollama for model serving"],
        )
        errors.append(f"Profile recommendation failed: {e}")

    result = {
        "schema_version": 1,
        "system": system.to_dict(),
        "gpus": [gpu.to_dict() for gpu in gpus],
        "capabilities": capabilities.to_dict(),
        "recommendation": profile.to_dict(),
    }

    if errors:
        result["errors"] = errors

    return result
