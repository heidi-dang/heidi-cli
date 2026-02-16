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

- **Config** - Global config stored in OS-specific location (not project-local):
  - Linux: `~/.config/heidi/` (or `$XDG_CONFIG_HOME/heidi`)
  - macOS: `~/Library/Application Support/Heidi`
  - Windows: `%APPDATA%/Heidi`
- **State** - Optional state in OS-specific location
- **Cache** - Optional cache in OS-specific location
- **Tasks** (`./tasks/`) - Task files (`<slug>.md`), audit files (`<slug>.audit.md`) - tracked in repo

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
| `heidi init` | Initialize global config directory |
| `heidi paths` | Show config/state/cache paths |
| `heidi update` | Update UI to latest version |
| `heidi upgrade` | Upgrade Heidi CLI |
| `heidi uninstall` | Uninstall Heidi CLI |
| `heidi auth gh` | Authenticate with GitHub |
| `heidi doctor` | Check all dependencies |
| `heidi copilot status` | Show Copilot connection status |
| `heidi copilot chat <msg>` | Chat with Copilot |
| `heidi run "prompt"` | Single prompt execution |
| `heidi loop "task"` | Full Plan→Audit loop |
| `heidi runs` | List recent runs |
| `heidi config` | Manage configuration |
| `heidi serve` | Start HTTP server (port 7777) |
| `heidi start ui` | Start UI dev server (port 3002) |
| `heidi openwebui status` | Check OpenWebUI connectivity |
| `heidi openwebui guide` | Show OpenWebUI setup guide |
| `heidi openwebui configure` | Configure OpenWebUI settings |
| `heidi connect status` | Show connection status (Ollama, OpenCode) |
| `heidi connect ollama` | Connect to Ollama |
| `heidi connect opencode` | Connect to OpenCode CLI or server |
| `heidi connect disconnect` | Disconnect from a service |

## Setup Wizard

The interactive setup wizard (`heidi setup`) guides you through:

1. **Environment Check** - Verifies Python, Copilot SDK, and optional tools
2. **Heidi Initialization** - Creates global config directory
3. **GitHub Authentication** - Sets up GitHub token for Copilot access
4. **OpenWebUI Integration** - Configures connection to OpenWebUI
5. **Final Summary** - Shows setup status and next steps

## Connect Commands

Connect to external services like Ollama and OpenCode:

```bash
# Check connection status for all services
heidi connect status
heidi connect status --json

# Connect to Ollama (default: http://127.0.0.1:11434)
heidi connect ollama
heidi connect ollama --url http://localhost:11434 --token <token> --save

# Connect to OpenCode CLI
heidi connect opencode --mode local

# Connect to OpenCode server (default: http://127.0.0.1:4096)
heidi connect opencode --mode server --url http://127.0.0.1:4096 --username <user>

# Disconnect from a service
heidi connect disconnect ollama --yes
heidi connect disconnect opencode --yes
```

### Connection Details

| Service | Default URL | Health Endpoint |
main
| Ollama | `http://127.0.0.1:11434` | `/api/version` |
| OpenCode Server | `http://127.0.0.1:4096` | `/global/health` |

## OpenWebUI Integration

Heidi CLI includes a built-in HTTP server for OpenWebUI integration:

```bash
# Start the server (foreground)
heidi serve

# Start with UI
heidi serve --ui

# Run in background and return immediately (writes PID to state dir)
heidi serve --detach

# Disable Rich rendering (useful for CI/non-TTY environments)
heidi serve --plain

# Or use environment variable
HEIDI_PLAIN=1 heidi serve
```

### Serve Options

| Option | Description |
|--------|-------------|
| `--host` | Host to bind to (default: 127.0.0.1) |
| `--port` | Port to bind to (default: 7777) |
| `--ui` | Also start UI dev server |
| `--detach`, `-d` | Run in background, return immediately (PID file in state dir) |
| `--plain` | Disable Rich rendering |
| `--force`, `-f` | Kill existing server before starting |

### Stopping Detached Server

```bash
# Find and kill by PID file
PID=$(cat ~/.local/state/heidi/server.pid)
kill $PID

# Or kill all heidi servers
pkill -f "heidi serve"
```

The server writes its PID to:
- Linux: `~/.local/state/heidi/server.pid`
- macOS: `~/Library/Application Support/Heidi/server.pid`
- Windows: `%LOCALAPPDATA%\Heidi\server.pid`

```bash
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

### Smoke Tests

**Linux/macOS (bash):**

```bash
bash scripts/smoke_cli.sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_cli.ps1
```

## Landing Page

The project includes a landing page hosted on Firebase Hosting at [heidi-cli.web.app](https://heidi-cli.web.app).

### Cloning with Submodules

This repository uses git submodules. To clone with all submodules:

```bash
git clone --recurse-submodules https://github.com/heidi-dang/heidi-cli
```

Or if you've already cloned:
```bash
git submodule update --init --recursive
```

### Landing Page Development

The landing page is in `heidi-cli-landing-page/`. To run it locally:

```bash
cd heidi-cli-landing-page
npm install
npm run dev
```

### Firebase Deployment

The landing page has automatic CI/CD via GitHub Actions:

- **Pull Requests**: Deploys to a Firebase preview channel
- **Merges to main**: Deploys to production live channel

#### Setting Up Firebase CI

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Hosting for your project
3. Create a service account:
   - Go to Project Settings → Service Accounts
   - Click "Generate new private key"
   - Copy the JSON content
4. Add the following GitHub Secrets:
   - `FIREBASE_SERVICE_ACCOUNT_HEIDI_CLI`: The JSON service account key (entire content)
   - `FIREBASE_PROJECT_ID`: Your Firebase project ID (e.g., `heidi-cli`)

#### Landing Page Environment Variables

For local development, create a `.env.local` file in `heidi-cli-landing-page/`:

```bash
GEMINI_API_KEY=your-gemini-api-key
```

Note: `.env.local` is gitignored and should never be committed.

## License

MIT
