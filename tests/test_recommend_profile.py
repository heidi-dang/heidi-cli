"""Table-driven tests for profile recommendation logic."""

import pytest
from heidi_cli.system_probe import (
    GPUInfo,
    GPUVendor,
    MLCapabilities,
    recommend_profile,
)


class TestRecommendProfileTableDriven:
    """Table-driven tests for profile recommendations."""

    @pytest.mark.parametrize(
        "gpu_memory_mb,vendor,cuda,rocm,mlx,expected_profile,expected_quantization,expected_memory_efficient",
        [
            # CPU-only cases
            (0, None, False, False, False, "cpu_rag_only", "4bit", True),
            # NVIDIA GPU cases
            (4096, GPUVendor.NVIDIA, True, False, False, "nvidia_4gb_inference", "4bit", True),
            (8192, GPUVendor.NVIDIA, True, False, False, "nvidia_8gb_qlora", "4bit", True),
            (16384, GPUVendor.NVIDIA, True, False, False, "nvidia_8gb_qlora", "4bit", True),
            (
                24576,
                GPUVendor.NVIDIA,
                True,
                False,
                False,
                "nvidia_24gb_full_finetune",
                "16bit",
                False,
            ),
            (
                32768,
                GPUVendor.NVIDIA,
                True,
                False,
                False,
                "nvidia_24gb_full_finetune",
                "16bit",
                False,
            ),
            # Apple Silicon cases
            (8192, GPUVendor.APPLE, False, False, True, "apple_silicon_8gb_mlx", "4bit", True),
            (16384, GPUVendor.APPLE, False, False, True, "apple_silicon_16gb_mlx", "8bit", True),
            (32768, GPUVendor.APPLE, False, False, True, "apple_silicon_16gb_mlx", "8bit", True),
            # AMD GPU cases
            (4096, GPUVendor.AMD, False, True, False, "amd_rocm_qlora", "4bit", True),
            (8192, GPUVendor.AMD, False, True, False, "amd_rocm_qlora", "4bit", True),
            (16384, GPUVendor.AMD, False, True, False, "amd_rocm_qlora", "4bit", True),
            (4096, GPUVendor.AMD, False, False, False, "amd_inference_only", "4bit", True),
            (8192, GPUVendor.AMD, False, False, False, "amd_inference_only", "4bit", True),
            # Unknown vendor fallback
            (8192, GPUVendor.UNKNOWN, False, False, False, "generic_inference", "4bit", True),
        ],
    )
    def test_profile_recommendations(
        self,
        gpu_memory_mb,
        vendor,
        cuda,
        rocm,
        mlx,
        expected_profile,
        expected_quantization,
        expected_memory_efficient,
    ):
        """Test profile recommendations based on GPU memory and capabilities."""
        system = Mock()

        # Create GPU if memory > 0
        gpus = []
        if gpu_memory_mb > 0 and vendor:
            gpu = GPUInfo(
                vendor=vendor,
                name=f"Test GPU {gpu_memory_mb}MB",
                memory_mb=gpu_memory_mb,
            )
            gpus.append(gpu)

        capabilities = MLCapabilities(
            cuda_available=cuda,
            rocm_available=rocm,
            mlx_available=mlx,
            torch_installed=True,
        )

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == expected_profile
        assert profile.quantization == expected_quantization
        assert profile.memory_efficient == expected_memory_efficient


class TestRecommendProfileEdgeCases:
    """Test edge cases for profile recommendations."""

    def test_empty_gpu_list(self):
        """Test recommendation with no GPUs."""
        system = Mock()
        gpus = []
        capabilities = MLCapabilities()

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == "cpu_rag_only"
        assert profile.memory_efficient is True
        assert "ollama" in " ".join(profile.next_steps).lower()

    def test_gpu_with_zero_memory(self):
        """Test recommendation with GPU that has 0 memory reported."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.NVIDIA,
                name="Unknown GPU",
                memory_mb=0,
            )
        ]
        capabilities = MLCapabilities(cuda_available=True)

        profile = recommend_profile(system, gpus, capabilities)

        # Should fall back to CPU-only profile
        assert profile.name == "cpu_rag_only"

    def test_multiple_gpus_selects_best(self):
        """Test that multiple GPUs selects the one with most memory."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.NVIDIA,
                name="RTX 3060",
                memory_mb=12288,  # 12GB
            ),
            GPUInfo(
                vendor=GPUVendor.NVIDIA,
                name="RTX 4090",
                memory_mb=24576,  # 24GB
            ),
        ]
        capabilities = MLCapabilities(cuda_available=True)

        profile = recommend_profile(system, gpus, capabilities)

        # Should recommend based on the 24GB GPU
        assert profile.name == "nvidia_24gb_full_finetune"
        assert profile.quantization == "16bit"
        assert profile.memory_efficient is False

    def test_mixed_gpu_vendors(self):
        """Test behavior with mixed GPU vendors."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.INTEL,
                name="Intel UHD",
                memory_mb=4096,  # 4GB
            ),
            GPUInfo(
                vendor=GPUVendor.NVIDIA,
                name="RTX 3080",
                memory_mb=10240,  # 10GB
            ),
        ]
        capabilities = MLCapabilities(cuda_available=True)

        profile = recommend_profile(system, gpus, capabilities)

        # Should recommend based on the NVIDIA GPU
        assert profile.name == "nvidia_8gb_qlora"

    def test_apple_silicon_without_mlx(self):
        """Test Apple Silicon without MLX available."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.APPLE,
                name="Apple M2",
                memory_mb=16384,
            )
        ]
        capabilities = MLCapabilities(mlx_available=False)

        profile = recommend_profile(system, gpus, capabilities)

        # Should still recommend Apple Silicon profile even without MLX
        assert profile.name == "apple_silicon_16gb_mlx"

    def test_amd_gpu_without_rocm(self):
        """Test AMD GPU without ROCm available."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.AMD,
                name="Radeon RX 6800",
                memory_mb=16384,
            )
        ]
        capabilities = MLCapabilities(rocm_available=False)

        profile = recommend_profile(system, gpus, capabilities)

        # Should recommend inference-only profile
        assert profile.name == "amd_inference_only"
        assert "inference" in profile.description.lower()


class TestRecommendProfileContent:
    """Test the content of recommended profiles."""

    def test_cpu_profile_content(self):
        """Test CPU-only profile has appropriate content."""
        system = Mock()
        gpus = []
        capabilities = MLCapabilities()

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == "cpu_rag_only"
        assert "CPU-only" in profile.description
        assert "RAG" in profile.description
        assert profile.memory_efficient is True
        assert profile.quantization == "4bit"

        # Should recommend small models
        assert any("1b" in model or "0.5b" in model for model in profile.recommended_models)

        # Should mention Ollama in next steps
        assert any("ollama" in step.lower() for step in profile.next_steps)

    def test_nvidia_high_end_profile_content(self):
        """Test high-end NVIDIA profile has appropriate content."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.NVIDIA,
                name="RTX 4090",
                memory_mb=24576,
            )
        ]
        capabilities = MLCapabilities(cuda_available=True, torch_installed=True)

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == "nvidia_24gb_full_finetune"
        assert "High-end" in profile.description
        assert "full fine-tuning" in profile.description
        assert profile.memory_efficient is False
        assert profile.quantization == "16bit"

        # Should recommend larger models
        assert any("8b" in model or "7b" in model for model in profile.recommended_models)

        # Should mention PyTorch installation
        assert any("torch" in step.lower() for step in profile.next_steps)

    def test_apple_silicon_profile_content(self):
        """Test Apple Silicon profile has appropriate content."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.APPLE,
                name="Apple M2",
                memory_mb=16384,
            )
        ]
        capabilities = MLCapabilities(mlx_available=True)

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == "apple_silicon_16gb_mlx"
        assert "MLX" in profile.description
        assert profile.memory_efficient is True

        # Should mention MLX in next steps
        assert any("mlx" in step.lower() for step in profile.next_steps)

    def test_amd_rocm_profile_content(self):
        """Test AMD ROCm profile has appropriate content."""
        system = Mock()
        gpus = [
            GPUInfo(
                vendor=GPUVendor.AMD,
                name="Radeon RX 7900 XTX",
                memory_mb=24576,
            )
        ]
        capabilities = MLCapabilities(rocm_available=True)

        profile = recommend_profile(system, gpus, capabilities)

        assert profile.name == "amd_rocm_qlora"
        assert "ROCm" in profile.description
        assert "QLoRA" in profile.description
        assert profile.memory_efficient is True

        # Should mention ROCm in next steps
        assert any("rocm" in step.lower() for step in profile.next_steps)


# Import Mock for the tests
from unittest.mock import Mock
