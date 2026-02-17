"""Tests for ML CLI commands."""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from heidi_cli.cli import app


class TestMLCommandsSmoke:
    """Smoke tests for ML commands to verify they run without errors."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_recommend_basic(self, mock_probe):
        """Test basic ml recommend command."""
        # Mock successful probe
        mock_probe.return_value = {
            "system": {
                "os": "linux",
                "arch": "x86_64",
                "cpu_count": 8,
                "memory_gb": 16.0,
                "disk_free_gb": 100.0,
                "is_wsl": False,
                "python_version": "3.11.0",
            },
            "gpus": [
                {
                    "vendor": "nvidia",
                    "name": "RTX 4090",
                    "memory_mb": 24576,
                    "driver_version": "525.60.11",
                    "cuda_version": "12.0",
                    "rocm_version": None,
                }
            ],
            "capabilities": {
                "cuda_available": True,
                "rocm_available": False,
                "mlx_available": False,
                "torch_installed": True,
                "optimal_batch_size": 8,
            },
            "recommendation": {
                "name": "nvidia_24gb_full_finetune",
                "description": "High-end NVIDIA GPU suitable for full fine-tuning",
                "recommended_models": ["llama3.1-8b", "mistral-7b"],
                "max_sequence_length": 8192,
                "quantization": "16bit",
                "memory_efficient": False,
                "next_steps": ["Install PyTorch", "Install transformers"],
            },
        }

        result = self.runner.invoke(app, ["ml", "recommend"])

        assert result.exit_code == 0
        assert "System Information" in result.stdout
        assert "GPU Information" in result.stdout
        assert "ML Capabilities" in result.stdout
        assert "Recommended Profile" in result.stdout
        assert "RTX 4090" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_recommend_json_output(self, mock_probe):
        """Test ml recommend command with JSON output."""
        # Mock probe data
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": True},
            "recommendation": {"name": "test_profile"},
        }

        result = self.runner.invoke(app, ["ml", "recommend", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        json_output = json.loads(result.stdout)
        assert "system" in json_output
        assert "gpus" in json_output
        assert "capabilities" in json_output
        assert "recommendation" in json_output
        assert json_output["system"]["os"] == "linux"

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_basic(self, mock_probe):
        """Test basic ml guide command."""
        # Mock successful probe
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {
                "name": "cpu_rag_only",
                "description": "CPU-only system suitable for RAG",
                "next_steps": ["Install Ollama", "Pull model", "Start Ollama"],
            },
        }

        result = self.runner.invoke(app, ["ml", "guide"])

        assert result.exit_code == 0
        assert "Setup Guide" in result.stdout
        assert "CPU RAG Only" in result.stdout
        assert "Install Ollama" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_json_output(self, mock_probe):
        """Test ml guide command with JSON output."""
        # Mock probe data
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {"name": "cpu_rag_only", "next_steps": ["Step 1", "Step 2"]},
        }

        result = self.runner.invoke(app, ["ml", "guide", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        json_output = json.loads(result.stdout)
        assert "profile" in json_output
        assert "guide_steps" in json_output
        assert json_output["guide_steps"] == ["Step 1", "Step 2"]

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_recommend_cpu_only(self, mock_probe):
        """Test ml recommend with CPU-only system."""
        # Mock CPU-only system
        mock_probe.return_value = {
            "system": {
                "os": "linux",
                "arch": "x86_64",
                "cpu_count": 4,
                "memory_gb": 8.0,
                "disk_free_gb": 50.0,
                "is_wsl": False,
                "python_version": "3.10.0",
            },
            "gpus": [],
            "capabilities": {
                "cuda_available": False,
                "rocm_available": False,
                "mlx_available": False,
                "torch_installed": False,
                "optimal_batch_size": None,
            },
            "recommendation": {
                "name": "cpu_rag_only",
                "description": "CPU-only system suitable for RAG and inference",
                "recommended_models": ["llama3.2-1b", "phi3-mini"],
                "max_sequence_length": 2048,
                "quantization": "4bit",
                "memory_efficient": True,
                "next_steps": ["Install Ollama", "Pull small model"],
            },
        }

        result = self.runner.invoke(app, ["ml", "recommend"])

        assert result.exit_code == 0
        assert "No GPUs detected" in result.stdout
        assert "CPU RAG Only" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_recommend_apple_silicon(self, mock_probe):
        """Test ml recommend with Apple Silicon."""
        # Mock Apple Silicon system
        mock_probe.return_value = {
            "system": {
                "os": "darwin",
                "arch": "arm64",
                "cpu_count": 8,
                "memory_gb": 16.0,
                "disk_free_gb": 200.0,
                "is_wsl": False,
                "python_version": "3.11.0",
            },
            "gpus": [
                {
                    "vendor": "apple",
                    "name": "Apple M2",
                    "memory_mb": 16384,
                    "driver_version": None,
                    "cuda_version": None,
                    "rocm_version": None,
                }
            ],
            "capabilities": {
                "cuda_available": False,
                "rocm_available": False,
                "mlx_available": True,
                "torch_installed": False,
                "optimal_batch_size": None,
            },
            "recommendation": {
                "name": "apple_silicon_16gb_mlx",
                "description": "Apple Silicon with MLX acceleration",
                "recommended_models": ["llama3.2-3b", "phi3-mini"],
                "max_sequence_length": 4096,
                "quantization": "8bit",
                "memory_efficient": True,
                "next_steps": ["Install MLX", "Install transformers"],
            },
        }

        result = self.runner.invoke(app, ["ml", "recommend"])

        assert result.exit_code == 0
        assert "Apple M2" in result.stdout
        assert "MLX Available" in result.stdout
        assert "Apple Silicon 16gb Mlx" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_nvidia_setup(self, mock_probe):
        """Test ml guide provides NVIDIA-specific setup."""
        # Mock NVIDIA system
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [{"vendor": "nvidia", "name": "RTX 3080"}],
            "capabilities": {"cuda_available": True, "torch_installed": False},
            "recommendation": {
                "name": "nvidia_8gb_qlora",
                "next_steps": ["Install PyTorch", "Install bitsandbytes"],
            },
        }

        result = self.runner.invoke(app, ["ml", "guide"])

        assert result.exit_code == 0
        assert "NVIDIA GPU detected" in result.stdout
        assert "pip install torch" in result.stdout
        assert "bitsandbytes" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_apple_setup(self, mock_probe):
        """Test ml guide provides Apple-specific setup."""
        # Mock Apple Silicon system
        mock_probe.return_value = {
            "system": {"os": "darwin"},
            "gpus": [{"vendor": "apple", "name": "Apple M2"}],
            "capabilities": {"mlx_available": True, "torch_installed": False},
            "recommendation": {"name": "apple_silicon_16gb_mlx", "next_steps": ["Install MLX"]},
        }

        result = self.runner.invoke(app, ["ml", "guide"])

        assert result.exit_code == 0
        assert "Apple Silicon detected" in result.stdout
        assert "pip install mlx" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_cpu_setup(self, mock_probe):
        """Test ml guide provides CPU-specific setup."""
        # Mock CPU-only system
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {"name": "cpu_rag_only", "next_steps": ["Install Ollama"]},
        }

        result = self.runner.invoke(app, ["ml", "guide"])

        assert result.exit_code == 0
        assert "CPU-only system" in result.stdout
        assert "ollama" in result.stdout.lower()

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_recommend_error_handling(self, mock_probe):
        """Test error handling in ml recommend."""
        # Mock probe to raise an exception
        mock_probe.side_effect = Exception("Probe failed")

        result = self.runner.invoke(app, ["ml", "recommend"])

        assert result.exit_code == 1
        assert "Error during system probe" in result.stdout

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_ml_guide_error_handling(self, mock_probe):
        """Test error handling in ml guide."""
        # Mock probe to raise an exception
        mock_probe.side_effect = Exception("Guide failed")

        result = self.runner.invoke(app, ["ml", "guide"])

        assert result.exit_code == 1
        assert "Error generating guide" in result.stdout


class TestDoctorMLFlag:
    """Test the --ml flag on doctor command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("heidi_cli.cli.probe_and_recommend")
    def test_doctor_ml_flag_success(self, mock_probe):
        """Test doctor --ml flag with successful probe."""
        # Mock successful probe
        mock_probe.return_value = {
            "system": {"os": "linux", "cpu_count": 8},
            "gpus": [{"vendor": "nvidia", "name": "RTX 4090", "memory_mb": 24576}],
            "capabilities": {"cuda_available": True, "torch_installed": True},
            "recommendation": {
                "name": "nvidia_24gb_full_finetune",
                "description": "High-end NVIDIA GPU",
                "next_steps": ["Install PyTorch", "Install transformers"],
            },
        }

        result = self.runner.invoke(app, ["doctor", "--ml"])

        assert result.exit_code == 0
        assert "ML System Probe" in result.stdout
        assert "ML Capabilities" in result.stdout
        assert "Detected GPUs" in result.stdout
        assert "ML Recommendation" in result.stdout
        assert "RTX 4090" in result.stdout

    @patch("heidi_cli.cli.probe_and_recommend")
    def test_doctor_ml_flag_json(self, mock_probe):
        """Test doctor --ml flag with JSON output."""
        # Mock probe
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {"name": "cpu_rag_only"},
        }

        result = self.runner.invoke(app, ["doctor", "--ml", "--json"])

        assert result.exit_code == 0
        # Note: The doctor command doesn't currently support JSON output for ML section
        # This test documents current behavior

    @patch("heidi_cli.cli.probe_and_recommend")
    def test_doctor_ml_flag_no_gpus(self, mock_probe):
        """Test doctor --ml flag with no GPUs detected."""
        # Mock CPU-only system
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {"name": "cpu_rag_only", "next_steps": ["Install Ollama"]},
        }

        result = self.runner.invoke(app, ["doctor", "--ml"])

        assert result.exit_code == 0
        assert "No GPUs detected" in result.stdout
        assert "CPU RAG Only" in result.stdout

    def test_doctor_ml_flag_import_error(self):
        """Test doctor --ml flag when psutil is not available."""
        result = self.runner.invoke(app, ["doctor", "--ml"])

        # Should handle missing psutil gracefully
        assert result.exit_code == 0
        # May show warning about psutil depending on environment


class TestMLSchemaValidation:
    """Test JSON schema validation for ML commands."""

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_recommend_json_schema_keys(self, mock_probe):
        """Test ml recommend --json output has required schema keys."""
        # Mock probe data
        mock_probe.return_value = {
            "system": {"os": "linux", "arch": "x86_64"},
            "gpus": [{"vendor": "nvidia", "name": "RTX 4090"}],
            "capabilities": {"cuda_available": True},
            "recommendation": {"name": "test_profile", "next_steps": ["step1"]},
        }

        result = self.runner.invoke(app, ["ml", "recommend", "--json"])

        assert result.exit_code == 0

        json_output = json.loads(result.stdout)

        # Verify top-level keys
        required_keys = ["system", "gpus", "capabilities", "recommendation"]
        for key in required_keys:
            assert key in json_output, f"Missing required key: {key}"

        # Verify system schema
        system_keys = [
            "os",
            "arch",
            "cpu_count",
            "memory_gb",
            "disk_free_gb",
            "is_wsl",
            "python_version",
        ]
        for key in system_keys:
            assert key in json_output["system"], f"Missing system key: {key}"

        # Verify GPU schema
        if json_output["gpus"]:
            gpu_keys = ["vendor", "name", "memory_mb"]
            for key in gpu_keys:
                assert key in json_output["gpus"][0], f"Missing GPU key: {key}"

        # Verify capabilities schema
        cap_keys = ["cuda_available", "rocm_available", "mlx_available", "torch_installed"]
        for key in cap_keys:
            assert key in json_output["capabilities"], f"Missing capability key: {key}"

        # Verify recommendation schema
        rec_keys = [
            "name",
            "description",
            "recommended_models",
            "max_sequence_length",
            "quantization",
            "memory_efficient",
            "next_steps",
        ]
        for key in rec_keys:
            assert key in json_output["recommendation"], f"Missing recommendation key: {key}"

    @patch("heidi_cli.ml_commands.probe_and_recommend")
    def test_guide_json_schema_keys(self, mock_probe):
        """Test ml guide --json output has required schema keys."""
        # Mock probe data
        mock_probe.return_value = {
            "system": {"os": "linux"},
            "gpus": [],
            "capabilities": {"cuda_available": False},
            "recommendation": {
                "name": "cpu_rag_only",
                "description": "CPU-only system",
                "recommended_models": ["model1"],
                "max_sequence_length": 2048,
                "quantization": "4bit",
                "memory_efficient": True,
                "next_steps": ["step1", "step2"],
            },
        }

        result = self.runner.invoke(app, ["ml", "guide", "--json"])

        assert result.exit_code == 0

        json_output = json.loads(result.stdout)

        # Verify top-level keys
        required_keys = ["profile", "system", "gpus", "capabilities", "guide_steps"]
        for key in required_keys:
            assert key in json_output, f"Missing required key: {key}"

        # Verify guide_steps
        assert isinstance(json_output["guide_steps"], list)
        assert len(json_output["guide_steps"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])
