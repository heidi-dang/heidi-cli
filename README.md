# Heidi-CLI

A modular agent orchestration framework for coordinating AI-powered development workflows with GitHub Copilot, Jules, and OpenCode.

## Overview

Heidi-CLI provides a flexible system for running AI-powered agent workflows with:

- **Multi-Agent Orchestration** - Coordinate Copilot SDK, Jules, and OpenCode agents
- **Plan→Run→Audit Workflow** - Strict workflow with durable artifacts
- **Python SDK** - Programmatic access via `client.py` and `sdk.py`
- **CLI Tooling** - Full-featured command-line interface

## Features

### Multi-Agent Support
- **GitHub Copilot** - AI-assisted code generation and conversation
- **Jules** - Google's coding agent
- **OpenCode** - Open source AI coding assistant

### Workflow Engine
- **Plan Phase** - Define agent tasks and handoffs
- **Run Phase** - Execute agents with proper routing
- **Audit Phase** - Verify changes and run verifications

### Developer Experience
- Interactive CLI with rich formatting
- Configurable agent templates
- Persistent workspace state
- Secret redaction for security

## Project Structure

```
.
├── heidi_cli/           # CLI tool for agent orchestration
├── client.py            # Python client for agent interaction
├── sdk.py               # GitHub Copilot SDK integration
└── .local/              # Local development files (ignored)
```

## Getting Started

### Prerequisites

- Python 3.10+
- GitHub Copilot subscription (for Copilot features)

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
# Initialize
heidi init

# Authenticate with GitHub
heidi auth gh

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
| `heidi init` | Initialize `.heidi/` directory |
| `heidi auth gh` | Authenticate with GitHub |
| `heidi doctor` | Check all dependencies |
| `heidi copilot status` | Show Copilot connection status |
| `heidi copilot chat <msg>` | Chat with Copilot |
| `heidi run "prompt"` | Single prompt execution |
| `heidi loop "task"` | Full Plan→Audit loop |
| `heidi runs` | List recent runs |
| `heidi config` | Manage configuration |
| `heidi serve` | Start HTTP server (port 7777) |

## Development

```bash
# Run tests
pytest heidi_cli/tests/ -v

# Lint code
ruff check heidi_cli/src/
```

## License

MIT
