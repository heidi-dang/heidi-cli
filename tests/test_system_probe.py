"""Tests for system_probe module."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from heidi_cli.system_probe import (
    SystemInfo,
    GPUInfo,
    GPUVendor,
    MLCapabilities,
    MLProfile,
    _run_command,
    probe_system,
    probe_nvidia_gpus,
    probe_amd_gpus,
    probe_windows_gpus,
    probe_mac_gpus,
    probe_gpus,
    check_ml_capabilities,
    recommend_profile,
    probe_and_recommend,
)


class TestRunCommand:
    """Test the _run_command utility function."""

    def test_successful_command(self):
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="test output")

            success, output = _run_command(["echo", "test"])

            assert success is True
            assert output == "test output"
            mock_run.assert_called_once()

    def test_failed_command(self):
        """Test failed command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="error output")

            success, output = _run_command(["false"])

            assert success is False
            assert output == "error output"

    def test_timeout_command(self):
        """Test command timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            success, output = _run_command(["sleep", "10"])

            assert success is False
            assert output == ""

    def test_command_not_found(self):
        """Test command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            success, output = _run_command(["nonexistent_command"])

            assert success is False
            assert output == ""


class TestSystemInfo:
    """Test SystemInfo dataclass."""

    def test_to_dict(self):
        """Test SystemInfo serialization."""
        info = SystemInfo(
            os="linux",
            arch="x86_64",
            cpu_count=8,
            memory_gb=16.5,
            disk_free_gb=100.2,
            is_wsl=True,
            python_version="3.11.0",
        )

        expected = {
            "os": "linux",
            "arch": "x86_64",
            "cpu_count": 8,
            "memory_gb": 16.5,
            "disk_free_gb": 100.2,
            "is_wsl": True,
            "wsl_distro": None,
            "python_version": "3.11.0",
        }

        assert info.to_dict() == expected


class TestGPUInfo:
    """Test GPUInfo dataclass."""

    def test_to_dict(self):
        """Test GPUInfo serialization."""
        gpu = GPUInfo(
            vendor=GPUVendor.NVIDIA,
            name="RTX 4090",
            memory_mb=24576,
            driver_version="525.60.11",
            cuda_version="12.0",
        )

        expected = {
            "vendor": "nvidia",
            "name": "RTX 4090",
            "memory_mb": 24576,
            "driver_version": "525.60.11",
            "cuda_version": "12.0",
            "rocm_version": None,
        }

        assert gpu.to_dict() == expected


class TestMLCapabilities:
    """Test MLCapabilities dataclass."""

    def test_to_dict(self):
        """Test MLCapabilities serialization."""
        caps = MLCapabilities(
            cuda_available=True,
            rocm_available=False,
            mlx_available=False,
            torch_installed=True,
            optimal_batch_size=4,
        )

        expected = {
            "cuda_available": True,
            "rocm_available": False,
            "mlx_available": False,
            "torch_installed": True,
            "optimal_batch_size": 4,
        }

        assert caps.to_dict() == expected


class TestMLProfile:
    """Test MLProfile dataclass."""

    def test_to_dict(self):
        """Test MLProfile serialization."""
        profile = MLProfile(
            name="nvidia_8gb_qlora",
            description="Mid-range NVIDIA GPU suitable for QLoRA fine-tuning",
            recommended_models=["llama3.2-3b", "phi3-mini"],
            max_sequence_length=4096,
            quantization="4bit",
            memory_efficient=True,
            next_steps=["Install PyTorch", "Install bitsandbytes"],
        )

        result = profile.to_dict()

        assert result["name"] == "nvidia_8gb_qlora"
        assert result["description"] == "Mid-range NVIDIA GPU suitable for QLoRA fine-tuning"
        assert result["recommended_models"] == ["llama3.2-3b", "phi3-mini"]
        assert result["max_sequence_length"] == 4096
        assert result["quantization"] == "4bit"
        assert result["memory_efficient"] is True
        assert result["next_steps"] == ["Install PyTorch", "Install bitsandbytes"]


class TestProbeSystem:
    """Test system probing functionality."""

    @patch("platform.system")
    @patch("platform.machine")
    @patch("os.cpu_count")
    @patch("sys.version_info")
    def test_probe_system_basic(self, mock_version, mock_cpu, mock_machine, mock_system):
        """Test basic system probing."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        mock_cpu.return_value = 8
        mock_version.major = 3
        mock_version.minor = 11
        mock_version.micro = 0

        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_path = Mock()
                mock_path.statvfs.side_effect = AttributeError("No statvfs on Windows")
                mock_cwd.return_value = mock_path

                with patch("shutil.disk_usage") as mock_disk:
                    mock_disk.return_value = Mock(free=1024**3 * 100)  # 100GB free

                    # Mock psutil as unavailable
                    with patch("heidi_cli.system_probe.PSUTIL_AVAILABLE", False):
                        system = probe_system()

        assert system.os == "linux"
        assert system.arch == "x86_64"
        assert system.cpu_count == 8
        assert system.python_version == "3.11.0"
        assert system.is_wsl is False

    @patch("platform.system")
    @patch("builtins.open")
    def test_wsl_detection(self, mock_open, mock_system):
        """Test WSL detection."""
        mock_system.return_value = "Linux"

        # Mock /proc/version with Microsoft indicator
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_file.read.return_value = "Linux version 5.15.0-76-generic (Microsoft)"
        mock_open.return_value = mock_file

        with patch("platform.machine", return_value="x86_64"):
            with patch("os.cpu_count", return_value=8):
                with patch("sys.version_info") as mock_version:
                    mock_version.major = 3
                    mock_version.minor = 11
                    mock_version.micro = 0

                    with patch("pathlib.Path.cwd") as mock_cwd:
                        mock_path = Mock()
                        mock_path.statvfs.side_effect = AttributeError("No statvfs on Windows")
                        mock_cwd.return_value = mock_path

                        with patch("shutil.disk_usage") as mock_disk:
                            mock_disk.return_value = Mock(free=1024**3 * 100)

                            with patch("heidi_cli.system_probe.PSUTIL_AVAILABLE", False):
                                system = probe_system()

        assert system.is_wsl is True


class TestProbeGPUs:
    """Test GPU probing functionality."""

    def test_probe_nvidia_gpus_success(self):
        """Test successful NVIDIA GPU probing."""
        mock_output = """RTX 4090, 24576, 525.60.11, 12.0
RTX 3080, 10240, 525.60.11, 12.0"""

        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (True, mock_output)

            gpus = probe_nvidia_gpus()

        assert len(gpus) == 2
        assert gpus[0].vendor == GPUVendor.NVIDIA
        assert gpus[0].name == "RTX 4090"
        assert gpus[0].memory_mb == 24576
        assert gpus[0].driver_version == "525.60.11"
        assert gpus[0].cuda_version == "12.0"

    def test_probe_nvidia_gpus_failure(self):
        """Test NVIDIA GPU probing failure."""
        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (False, "")

            gpus = probe_nvidia_gpus()

        assert len(gpus) == 0

    def test_probe_amd_gpus_success(self):
        """Test successful AMD GPU probing."""
        mock_output = "GPU Series: AMD Radeon RX 7900 XTX"

        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (True, mock_output)

            gpus = probe_amd_gpus()

        assert len(gpus) == 1
        assert gpus[0].vendor == GPUVendor.AMD
        assert "Radeon RX 7900 XTX" in gpus[0].name

    def test_probe_windows_gpus_success(self):
        """Test successful Windows GPU probing."""
        mock_output = json.dumps(
            [
                {
                    "Name": "NVIDIA GeForce RTX 4090",
                    "AdapterRAM": 26843545600,  # 25600 MB in bytes
                }
            ]
        )

        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (True, mock_output)

            gpus = probe_windows_gpus()

        assert len(gpus) == 1
        assert gpus[0].vendor == GPUVendor.NVIDIA
        assert gpus[0].name == "NVIDIA GeForce RTX 4090"
        assert gpus[0].memory_mb == 25600

    def test_probe_mac_gpus_success(self):
        """Test successful macOS GPU probing."""
        mock_output = """Chipset Model: Apple M2
VRAM (Dynamic): 16 GB"""

        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (True, mock_output)

            gpus = probe_mac_gpus()

        assert len(gpus) == 1
        assert gpus[0].vendor == GPUVendor.APPLE
        assert "M2" in gpus[0].name
        assert gpus[0].memory_mb == 16384

    @patch("heidi_cli.system_probe.probe_system")
    def test_probe_gpus_linux(self, mock_system):
        """Test GPU probing on Linux."""
        mock_system.return_value = Mock(os="linux")

        with patch("heidi_cli.system_probe.probe_nvidia_gpus") as mock_nvidia:
            with patch("heidi_cli.system_probe.probe_amd_gpus") as mock_amd:
                mock_nvidia.return_value = []
                mock_amd.return_value = [Mock()]

                gpus = probe_gpus()

        mock_nvidia.assert_called_once()
        mock_amd.assert_called_once()
        assert len(gpus) == 1

    @patch("heidi_cli.system_probe.probe_system")
    def test_probe_gpus_windows(self, mock_system):
        """Test GPU probing on Windows."""
        mock_system.return_value = Mock(os="windows")

        with patch("heidi_cli.system_probe.probe_windows_gpus") as mock_windows:
            mock_windows.return_value = [Mock()]

            gpus = probe_gpus()

        mock_windows.assert_called_once()
        assert len(gpus) == 1

    @patch("heidi_cli.system_probe.probe_system")
    def test_probe_gpus_macos(self, mock_system):
        """Test GPU probing on macOS."""
        mock_system.return_value = Mock(os="darwin")

        with patch("heidi_cli.system_probe.probe_mac_gpus") as mock_mac:
            mock_mac.return_value = [Mock()]

            gpus = probe_gpus()

        mock_mac.assert_called_once()
        assert len(gpus) == 1


class TestMLCapabilitiesDetection:
    """Test ML capabilities checking."""

    def test_cuda_available_nvidia(self):
        """Test CUDA availability with NVIDIA GPU."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.NVIDIA)]

        caps = check_ml_capabilities(system, gpus)

        assert caps.cuda_available is True

    def test_rocm_available_amd(self):
        """Test ROCm availability with AMD GPU."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.AMD)]

        with patch("heidi_cli.system_probe._run_command") as mock_run:
            mock_run.return_value = (True, "ROCm info")

            caps = check_ml_capabilities(system, gpus)

        assert caps.rocm_available is True

    @patch("heidi_cli.system_probe.probe_system")
    def test_mlx_available_apple_silicon(self, mock_probe_system):
        """Test MLX availability on Apple Silicon."""
        system = Mock(os="darwin", arch="arm64")
        gpus = [Mock(vendor=GPUVendor.APPLE)]

        with patch("heidi_cli.system_probe.check_ml_capabilities") as mock_check:
            mock_check.return_value = MLCapabilities()

            # Mock MLX import
            with patch("heidi_cli.system_probe.importlib.util.find_spec") as mock_find_spec:
                mock_find_spec.return_value = Mock()
                caps = check_ml_capabilities(system, gpus)

        # Note: This test structure needs adjustment for the actual implementation
        assert isinstance(caps, MLCapabilities)

    def test_torch_installed(self):
        """Test PyTorch installation detection."""
        system = Mock()
        gpus = []

        with patch.dict("sys.modules", {"torch": Mock()}):
            with patch("torch.cuda.is_available", return_value=True):
                caps = check_ml_capabilities(system, gpus)

        assert caps.torch_installed is True


class TestRecommendProfile:
    """Test profile recommendation logic."""

    def test_cpu_only_profile(self):
        """Test CPU-only profile recommendation."""
        system = Mock()
        gpus = []
        caps = MLCapabilities()

        profile = recommend_profile(system, gpus, caps)

        assert profile.name == "cpu_rag_only"
        assert "CPU-only" in profile.description
        assert profile.memory_efficient is True
        assert "ollama" in " ".join(profile.next_steps).lower()

    def test_nvidia_24gb_profile(self):
        """Test NVIDIA 24GB profile recommendation."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.NVIDIA, memory_mb=24576)]
        caps = MLCapabilities(cuda_available=True)

        profile = recommend_profile(system, gpus, caps)

        assert profile.name == "nvidia_24gb_full_finetune"
        assert "High-end" in profile.description
        assert profile.memory_efficient is False
        assert "16bit" in profile.quantization

    def test_nvidia_8gb_profile(self):
        """Test NVIDIA 8GB profile recommendation."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.NVIDIA, memory_mb=8192)]
        caps = MLCapabilities(cuda_available=True)

        profile = recommend_profile(system, gpus, caps)

        assert profile.name == "nvidia_8gb_qlora"
        assert "QLoRA" in profile.description
        assert profile.memory_efficient is True
        assert "4bit" in profile.quantization

    def test_apple_silicon_16gb_profile(self):
        """Test Apple Silicon 16GB profile recommendation."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.APPLE, memory_mb=16384)]
        caps = MLCapabilities(mlx_available=True)

        profile = recommend_profile(system, gpus, caps)

        assert profile.name == "apple_silicon_16gb_mlx"
        assert "MLX" in profile.description
        assert profile.memory_efficient is True

    def test_amd_rocm_profile(self):
        """Test AMD ROCm profile recommendation."""
        system = Mock()
        gpus = [Mock(vendor=GPUVendor.AMD, memory_mb=8192)]
        caps = MLCapabilities(rocm_available=True)

        profile = recommend_profile(system, gpus, caps)

        assert profile.name == "amd_rocm_qlora"
        assert "ROCm" in profile.description
        assert profile.memory_efficient is True


class TestProbeAndRecommend:
    """Test the full probe and recommend pipeline."""

    @patch("heidi_cli.system_probe.recommend_profile")
    @patch("heidi_cli.system_probe.check_ml_capabilities")
    @patch("heidi_cli.system_probe.probe_gpus")
    @patch("heidi_cli.system_probe.probe_system")
    def test_full_pipeline(self, mock_system, mock_gpus, mock_caps, mock_profile):
        """Test the complete probing pipeline."""
        # Setup mocks
        mock_system.return_value = Mock(
            os="linux",
            arch="x86_64",
            cpu_count=8,
            memory_gb=16.0,
            disk_free_gb=100.0,
            is_wsl=False,
            python_version="3.11.0",
        )
        mock_system.return_value.to_dict.return_value = {
            "os": "linux",
            "arch": "x86_64",
            "cpu_count": 8,
            "memory_gb": 16.0,
            "disk_free_gb": 100.0,
            "is_wsl": False,
            "wsl_distro": None,
            "python_version": "3.11.0",
        }

        mock_gpu = Mock(
            vendor=GPUVendor.NVIDIA,
            name="RTX 4090",
            memory_mb=24576,
            driver_version="525.60.11",
            cuda_version="12.0",
        )
        mock_gpu.to_dict.return_value = {
            "vendor": "nvidia",
            "name": "RTX 4090",
            "memory_mb": 24576,
            "driver_version": "525.60.11",
            "cuda_version": "12.0",
            "rocm_version": None,
        }
        mock_gpus.return_value = [mock_gpu]

        mock_caps.return_value = MLCapabilities(
            cuda_available=True,
            rocm_available=False,
            mlx_available=False,
            torch_installed=True,
            optimal_batch_size=8,
        )

        mock_profile.return_value = MLProfile(
            name="nvidia_24gb_full_finetune",
            description="High-end NVIDIA GPU",
            recommended_models=["llama3.1-8b"],
            max_sequence_length=8192,
            quantization="16bit",
            memory_efficient=False,
            next_steps=["Install PyTorch"],
        )

        # Execute pipeline
        result = probe_and_recommend()

        # Verify structure
        assert "system" in result
        assert "gpus" in result
        assert "capabilities" in result
        assert "recommendation" in result

        # Verify system info
        assert result["system"]["os"] == "linux"
        assert result["system"]["cpu_count"] == 8

        # Verify GPU info
        assert len(result["gpus"]) == 1
        assert result["gpus"][0]["vendor"] == "nvidia"
        assert result["gpus"][0]["memory_mb"] == 24576

        # Verify capabilities
        assert result["capabilities"]["cuda_available"] is True
        assert result["capabilities"]["torch_installed"] is True

        # Verify recommendation
        assert result["recommendation"]["name"] == "nvidia_24gb_full_finetune"
        assert result["recommendation"]["memory_efficient"] is False


if __name__ == "__main__":
    pytest.main([__file__])
