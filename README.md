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

## Storage

- **State** (`.heidi/`) - Config, secrets, auth, valves (project-local, not tracked)
- **Artifacts** (`./tasks/`) - Task files (`<slug>.md`), audit files (`<slug>.audit.md`) - tracked in repo

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

### One-Click Installation

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1 | iex
```

### Manual Installation

```bash
# Install CLI from repo root
python -m pip install -e '.[dev]'
```

### Quick Start

```bash
# Run setup wizard (recommended for first-time users)
heidi setup

# Or initialize with defaults
heidi init

# Authenticate with GitHub
heidi auth gh

# Check Copilot status
heidi copilot status

# Chat with Copilot
heidi copilot chat "hello world"

# Run agent loop
heidi loop "fix failing tests" --executor copilot

# Start HTTP server for OpenWebUI integration
heidi serve

# Check OpenWebUI status
heidi openwebui status

# Get OpenWebUI setup guide
heidi openwebui guide
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `heidi setup` | Interactive setup wizard for first-time users |
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
| `heidi openwebui status` | Check OpenWebUI connectivity |
| `heidi openwebui guide` | Show OpenWebUI setup guide |
| `heidi openwebui configure` | Configure OpenWebUI settings |

## Setup Wizard

The interactive setup wizard (`heidi setup`) guides you through:

1. **Environment Check** - Verifies Python, Copilot SDK, and optional tools
2. **Heidi Initialization** - Creates `.heidi/` directory and config files
3. **GitHub Authentication** - Sets up GitHub token for Copilot access
4. **OpenWebUI Integration** - Configures connection to OpenWebUI
5. **Final Summary** - Shows setup status and next steps

## OpenWebUI Integration

Heidi CLI includes a built-in HTTP server for OpenWebUI integration:

```bash
# Start the server
heidi serve

# Check OpenWebUI status
heidi openwebui status

# Get setup guide
heidi openwebui guide

# Configure OpenWebUI settings
heidi openwebui configure --url http://localhost:3000 --token YOUR_TOKEN
```

The server provides these endpoints for OpenWebUI:
- `GET /health` - Health check
- `GET /agents` - List available agents
- `GET /runs` - List recent runs
- `GET /runs/{id}` - Get run details
- `GET /runs/{id}/stream` - Stream run events (SSE)
- `POST /run` - Execute single prompt
- `POST /loop` - Execute full agent loop

## Development

```bash
# Install
python -m pip install -e '.[dev]'

# Run tests
pytest -q

# Lint code
ruff check src
```

## License

MIT
