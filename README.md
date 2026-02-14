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
bash -c "$(curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh)"
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

## Product Test Flow

### Local Demo (Terminal + UI)

**Terminal A - Start Backend and UI:**
```bash
# From heidi-cli root
cd ui && npm install

# Start both backend + UI (from heidi-cli root)
heidi serve --ui

# Or start separately:
# Terminal A1: heidi serve
# Terminal A2: cd ui && npm run dev -- --port 3000
```

**Browser:**
```
http://localhost:3000
```

**Test Checklist:**
- [ ] Health check works (UI shows connected)
- [ ] Run mode → POST /run executes
- [ ] Loop mode → POST /loop executes
- [ ] Streaming shows live updates (or polling fallback works)
- [ ] Run list shows recent runs via /runs?limit=10

### Tunneling (Production)

Before exposing via Cloudflared:

1. **Enable API Key Auth:**
```bash
export HEIDI_API_KEY=your-secret-key
heidi serve
```

2. **Configure CORS (if needed):**
```bash
export HEIDI_CORS_ORIGINS=http://localhost:3000,https://your-tunnel-url
```

3. **UI calls must include:**
   - Header: `X-Heidi-Key: your-secret-key`
   - For SSE streaming: `/runs/{id}/stream?key=your-secret-key`

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
