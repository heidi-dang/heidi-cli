# Heidi Unified Learning Suite

A self-improving, modular AI suite for local model hosting, runtime learning, and offline dataset curation.

> [!NOTE]
> **Heidi-CLI has been evolved into the Unified Learning Suite.** Legacy agent orchestration features (Copilot SDK, Jules, OpenWebUI) have been removed to focus on a local-first learning loop.

## 🚀 The New Learning Loop

Heidi now provides a complete feedback loop for local AI development:

1.  **Multi-Model Host:** Serve multiple local LLMs via an OpenAI-compatible API.
2.  **Runtime Learning:** Models gain experience through memory, reflection, and reward scoring.
3.  **Data Pipeline:** Raw runs are captured, redacted, and curated into training datasets.
4.  **Self-Improvement:** Background retraining, evaluation gates, and atomic hot-swapping.

## 🛠 Modules

- `model_host/`: OpenAI-compatible multi-model routing.
- `runtime/`: Memory layers, reflection, and strategy ranking.
- `pipeline/`: Data capture, curation, and secret redaction.
- `registry/`: Versioning, eval gates, and promotion logic.

## 📦 Getting Started

### Installation

```bash
python -m pip install -e .
```

### Initialize the Suite

```bash
heidi status
```

This will initialize your persistent state root (default: `./state`).

### Serve Models

```bash
heidi model serve
```

The host will listen on `http://127.0.0.1:8000` and provide:
- `GET /v1/models`
- `POST /v1/chat/completions`

## 🩺 Doctor

Verify your installation and modular structure:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 scripts/doctor.py
```

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [Model Host](docs/model-host.md)
- [Auto-Registration](docs/auto-registration.md)

---
*Heidi is building the future of local, autonomous AI learning.*
