# Local ML Fine-Tuning with Heidi CLI

Heidi CLI provides built-in helpers for local ML fine-tuning, automatically detecting your hardware and recommending optimal setups.

## Quick Start

```bash
# Install ML dependencies
pip install heidi-cli[ml]

# Probe your system and get recommendations
heidi ml recommend

# Get tailored setup guide
heidi ml guide

# Include ML info in health check
heidi doctor --ml
```

## Understanding RAG vs LoRA

### RAG (Retrieval-Augmented Generation)
- **What it is**: Enhances model responses with retrieved context from your documents
- **Best for**: Knowledge-based tasks, Q&A over documents, maintaining factual accuracy
- **Hardware requirements**: Lower - can run on CPU or modest GPU
- **Setup**: Index your documents, then retrieve relevant context during inference

### LoRA (Low-Rank Adaptation)
- **What it is**: Parameter-efficient fine-tuning that adapts a model to your specific style/domain
- **Best for**: Adapting writing style, domain-specific terminology, task specialization
- **Hardware requirements**: Higher - needs GPU memory proportional to model size
- **Setup**: Train adapter layers on your examples, then use the adapted model

## Hardware Profiles

Heidi CLI automatically detects your hardware and recommends one of these profiles:

### CPU-Only Profiles

| Profile | Use Case | Recommended Models | Memory |
|---------|----------|-------------------|--------|
| `cpu_rag_only` | RAG and inference | llama3.2-1b, phi3-mini, qwen2-0.5b | 8GB+ RAM |

### NVIDIA GPU Profiles

| Profile | GPU Memory | Use Case | Recommended Models | Quantization |
|---------|------------|----------|-------------------|-------------|
| `nvidia_24gb_full_finetune` | 24GB+ | Full fine-tuning | llama3.1-8b, mistral-7b | 16-bit |
| `nvidia_8gb_qlora` | 8GB+ | QLoRA fine-tuning | llama3.2-3b, phi3-mini | 4-bit |
| `nvidia_4gb_inference` | 4GB+ | Inference/small training | llama3.2-1b, phi3-mini | 4-bit |

### Apple Silicon Profiles

| Profile | Unified Memory | Use Case | Recommended Models | Framework |
|---------|----------------|----------|-------------------|-----------|
| `apple_silicon_16gb_mlx` | 16GB+ | MLX fine-tuning | llama3.2-3b, phi3-mini | MLX |
| `apple_silicon_8gb_mlx` | 8GB+ | Memory-constrained MLX | llama3.2-1b, phi3-mini | MLX |

### AMD GPU Profiles

| Profile | ROCm Support | Use Case | Recommended Models |
|---------|--------------|----------|-------------------|
| `amd_rocm_qlora` | Yes | QLoRA training | llama3.2-3b, phi3-mini |
| `amd_inference_only` | No | Inference only | llama3.2-1b, phi3-mini |

## Command Reference

### `heidi ml recommend`

Probes your system and displays:
- System information (OS, CPU, RAM, disk)
- GPU details (vendor, model, memory)
- ML capabilities (CUDA, ROCm, MLX, PyTorch)
- Recommended profile with next steps

**Options:**
- `--json`: Output machine-readable JSON

**Example:**
```bash
heidi ml recommend --json > ml-profile.json
```

### `heidi ml guide`

Provides step-by-step setup instructions based on your detected profile.

**Options:**
- `--json`: Output guide steps in JSON format

**Example:**
```bash
heidi ml guide
```

### `heidi doctor --ml`

Extends the health check with ML system probing.

**Options:**
- `--ml`: Include ML capabilities and recommendations

**Example:**
```bash
heidi doctor --ml
```

## Security and Privacy

### Local-Only Operation
- **No network calls**: All hardware probing happens locally
- **No data upload**: Hardware specifications never leave your machine
- **Telemetry respects config**: ML probing follows your global telemetry settings

### What Gets Detected
- OS version and architecture
- CPU core count
- Total RAM and free disk space
- GPU vendor, model, and memory
- Python and ML framework versions
- WSL detection on Linux

### What Doesn't Get Sent
- Personal files or data
- Specific hardware serial numbers
- Usage patterns or statistics
- Model weights or training data

## Installation

### Basic Installation
```bash
pip install heidi-cli
```

### With ML Dependencies
```bash
pip install heidi-cli[ml]
```

### Manual ML Dependencies
If you prefer to install manually:
```bash
pip install heidi-cli
pip install psutil>=7.2.2
```

## Platform-Specific Setup

### NVIDIA GPUs
```bash
# Install PyTorch with CUDA
pip install torch torchvision torchaudio

# For QLoRA training
pip install bitsandbytes peft

# Verify CUDA availability
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### Apple Silicon
```bash
# Install MLX framework
pip install mlx mlx-lm

# Install transformers for model loading
pip install transformers

# Verify MLX availability
python -c "import mlx.core; print('MLX available')"
```

### AMD GPUs with ROCm
```bash
# Install PyTorch with ROCm support
pip install torch --index-url https://download.pytorch.org/whl/rocm

# Verify ROCm availability
python -c "import torch; print('ROCm available:', torch.cuda.is_available())"
```

### CPU-Only Systems
```bash
# Install Ollama for easy model serving
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a small model
ollama pull llama3.2:1b

# Start Ollama server
ollama serve
```

## Troubleshooting

### Common Issues

**"ML probing requires psutil"**
```bash
pip install psutil>=7.2.2
# or
pip install heidi-cli[ml]
```

**"CUDA not available"** (NVIDIA GPUs)
- Check NVIDIA driver installation: `nvidia-smi`
- Verify PyTorch CUDA installation
- Ensure CUDA version matches driver

**"ROCm not available"** (AMD GPUs)
- Install ROCm drivers from AMD
- Use ROCm-enabled PyTorch build
- Check `rocminfo` command works

**"MLX not available"** (Apple Silicon)
- Ensure you're on Apple Silicon (M1/M2/M3)
- Install MLX: `pip install mlx mlx-lm`
- Check architecture: `uname -m` should show `arm64`

### Debug Mode
Use verbose output to debug probing issues:
```bash
heidi --verbose ml recommend
```

### JSON Output
For programmatic use:
```bash
heidi ml recommend --json
heidi ml guide --json
heidi doctor --ml --json
```

## Integration Examples

### Bash Script Setup
```bash
#!/bin/bash
# Auto-setup based on detected profile

profile=$(heidi ml recommend --json | jq -r '.recommendation.name')

case $profile in
  nvidia_*)
    pip install torch torchvision torchaudio
    if [[ $profile == *"qlora"* ]]; then
      pip install bitsandbytes peft
    fi
    ;;
  apple_silicon_*)
    pip install mlx mlx-lm
    ;;
  cpu_*)
    curl -fsSL https://ollama.ai/install.sh | sh
    ;;
esac
```

### Python Integration
```python
import subprocess
import json

# Get ML profile
result = subprocess.run(["heidi", "ml", "recommend", "--json"], 
                       capture_output=True, text=True)
data = json.loads(result.stdout)

profile = data["recommendation"]["name"]
gpus = data["gpus"]

print(f"Detected profile: {profile}")
print(f"GPUs: {len(gpus)} detected")
```

## Contributing

The ML probing system is designed to be extensible. To add support for new hardware or frameworks:

1. Update `src/heidi_cli/system_probe.py`
2. Add new profiles to the `recommend_profile()` function
3. Add tests in `tests/test_system_probe.py`
4. Update documentation

See the development guide for more details.
