# Agents Loop Logic

A modular agent orchestration framework integrating GitHub Copilot SDK with customizable agent workflows.

## Overview

Agents Loop Logic provides a flexible system for running AI-powered agent workflows. It combines:

- **GitHub Copilot SDK** - For AI-assisted code generation and conversation
- **Agent Templates** - Reusable agent configurations in `Agents/`
- **CLI Tooling** - Command-line interface in `heidi_cli/`
- **Python SDK** - Programmatic access via `sdk.py` and `client.py`

## Project Structure

```
.
├── Agents/              # Agent definition templates
├── heidi_cli/          # CLI tool for agent orchestration
├── client.py           # Python client for agent interaction
├── sdk.py              # GitHub Copilot SDK integration
└── .local/             # Local development files (ignored)
```

## Getting Started

### Prerequisites

- Python 3.10+
- GitHub Copilot subscription

### Installation

```bash
# Install CLI
cd heidi_cli
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure GitHub Copilot
heidi config set copilot-token <your-token>
```

### Quick Start

```bash
# Check Copilot status
heidi copilot status

# Chat with Copilot
heidi copilot chat "hello world"

# Run agent loop
heidi loop "fix failing tests" --executor copilot
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `heidi copilot status` | Check Copilot connection |
| `heidi copilot chat <msg>` | Send message to Copilot |
| `heidi loop <task>` | Run agent loop for task |
| `heidi config` | Manage configuration |

## Development

```bash
# Run tests
pytest heidi_cli/tests/ -v

# Lint code
ruff check heidi_cli/src/
```

## License

MIT
