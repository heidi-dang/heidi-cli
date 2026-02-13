# Heidi CLI

Master controller that orchestrates Copilot SDK + Jules + OpenCode agent loops with strict Plan→Runner→Audit workflow and durable artifacts.

## Install

```bash
cd heidi_cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
# Initialize
heidi init

# Authenticate with GitHub
heidi auth gh

# Chat with Copilot
heidi copilot chat "hello"

# Run full loop
heidi loop "create hello.py prints hello" --executor copilot
```

## Commands

| Command | Description |
|---------|-------------|
| `heidi init` | Initialize `.heidi/` directory |
| `heidi auth gh` | Authenticate with GitHub |
| `heidi doctor` | Check all dependencies |
| `heidi copilot doctor` | Check Copilot SDK status |
| `heidi copilot status` | Show Copilot connection status |
| `heidi copilot chat "prompt"` | Chat with Copilot |
| `heidi run "prompt"` | Single prompt execution |
| `heidi loop "task"` | Full Plan→Audit loop |
| `heidi runs` | List recent runs |
| `heidi valves get/set` | Config management |
| `heidi serve` | Start HTTP server (port 7777) |
