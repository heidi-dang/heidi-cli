# Unified Learning Suite Architecture

The Unified Learning Suite for OpenCode is designed as a modular, self-improving AI system that runs locally. It bridges the gap between static model serving and dynamic runtime learning.

## Core Modules

- **Model Host (`src/model_host/`):** An OpenAI-compatible API that hosts multiple local models. It handles routing, loading, and atomic hot-swapping of model versions.
- **Runtime Learning (`src/runtime/`):** The "brain" of the suite. Implements short-term and long-term memory, reflection on experiences, reward scoring, and strategy selection.
- **Data Pipeline (`src/pipeline/`):** Collects raw trace data from runs, redacts secrets, and builds curated datasets for retraining.
- **Model Registry (`src/registry/`):** Manages model versions across `stable`, `candidate`, and `experimental` channels. Controls the evaluation and promotion gate.
- **Shared (`src/shared/`):** Common utilities, configuration management, and the persistent state root handler.

## Persistent State Root (`state/`)

Everything is stored in a unified root to ensure persistence across restarts:
- `config/`: Suite settings.
- `memory/`: SQLite and vector databases.
- `events/`: Runtime event logs.
- `datasets/`: Raw and curated training data.
- `models/`: Versioned model storage.

## Growth Model (4 Phases)

1. **Phase 1 (Foundation):** Establish the modular structure and the multi-model API host.
2. **Phase 2 (Experience):** Enable memory, reflection, and reward scoring during live usage.
3. **Phase 3 (Knowledge):** Capture runs and build redacted datasets for training.
4. **Phase 4 (Self-Improvement):** Background retraining, evaluation, and safe hot-swapping.
