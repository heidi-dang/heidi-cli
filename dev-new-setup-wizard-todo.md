# TODO — 1‑Click Install + First‑Run Wizard + OpenWebUI Connection (heidi-cli)

Branch: `feat/setup-wizard` (from `main`)

## Goal
A brand-new user can:
1) install Heidi CLI in **one step**
2) run `heidi` and get a **step-by-step wizard** that sets up everything
3) connect Heidi to **OpenWebUI** and verify the connection
4) run status checks anytime (non-interactive)

## Non‑negotiables
- **Never print tokens/secrets** (no logs, no stdout)
- Keep **project-local state** in `./.heidi/`
- Keep durable artifacts in `./tasks/`
- Terminal-first (no VS Code dependency)
- Minimal changes; avoid refactors unless required

---

## A) One‑click install (repo root)
Create these files in repo root:

### 1) `install.sh` (macOS/Linux)
- Ensure `pipx` exists (install if missing)
- Install from GitHub:
  - `pipx install git+https://github.com/heidi-dang/heidi-cli.git`
- Print final instructions: `Run: heidi`

### 2) `install.ps1` (Windows PowerShell)
- Verify `py` exists
- Install/ensure pipx:
  - `py -m pip install --user pipx`
  - `py -m pipx ensurepath`
- Install from GitHub:
  - `pipx install git+https://github.com/heidi-dang/heidi-cli.git`
- Print: “Open a new terminal, then run: heidi”

### 3) README updates
Add “One‑click install” section with the **exact commands** for:
- Linux/macOS
- Windows (PowerShell)

---

## B) First‑run wizard (automatic)
### Requirement
If the user runs **`heidi` with no args** and the project is not initialized (e.g. missing `./.heidi/config.json`), automatically start the wizard.

Add explicit command:
- `heidi setup` → runs wizard anytime

---

## C) Wizard steps (must be step-by-step)
Use Typer prompts + Rich output (simple panels/checklists).

### Step 1 — Environment checks
Display checklist:
- Python OK
- State dir: `./.heidi/`
- Tasks dir: `./tasks/`
- Heidi server base: `http://localhost:7777`

### Step 2 — Initialize project state
- Create `./.heidi/` and required config files
- Ensure secrets file permissions **0600**
- Ensure `/.heidi/` is gitignored (**either**: add it, or print clear instruction to add it)

### Step 3 — GitHub/Copilot setup
Prompt:
- “Configure GitHub token now?” (default YES)
- Token input hidden
Then run and show PASS/FAIL:
- `heidi auth status` (must not show token)
- `heidi copilot doctor`
- optionally `heidi copilot chat "hello"`

### Step 4 — OpenWebUI setup + API status check
Prompt:
- OpenWebUI URL (default `http://localhost:3000`)
- OpenWebUI API key (hidden; allow skip)
Save values.

Status check must:
- call an OpenWebUI API endpoint (e.g. list models)
- report PASS/FAIL with hints:
  - connection refused → OpenWebUI not running
  - 401 → invalid token
  - 200 → OK

### Step 5 — Heidi server health check
If server not running:
- ask “Start `heidi serve` now?” (default YES)
Then verify:
- `GET http://localhost:7777/health` returns OK

### Step 6 — OpenWebUI Tools connection guide (must print exact URL)
Print instructions to connect Heidi into OpenWebUI as OpenAPI tools using:
- `http://localhost:7777/openapi.json`

Also print quick test URLs:
- `/health`
- `/agents`
- `/runs/<id>`
- `/runs/<id>/stream` (SSE)

### Step 7 — Final summary
Print a final table with ✅/❌ for:
- Initialized project state
- GitHub token configured (or skipped)
- Copilot doctor
- OpenWebUI reachable
- Heidi server reachable
- OpenWebUI tool URL shown

---

## D) Non‑interactive helper commands (must add)
### 1) `heidi openwebui status`
- Reads saved OpenWebUI config
- Calls OpenWebUI API
- Prints single-line status and returns exit code:
  - 0 = OK
  - 1 = not configured
  - 2 = unreachable
  - 3 = unauthorized

### 2) `heidi openwebui guide`
- Prints the exact OpenWebUI connection instructions + URLs
- No network calls

---

## Definition of Done (PR checklist)
PR **must include** completed checklist + command output:

### Install
- [ ] `install.sh` works (mac/linux)
- [ ] `install.ps1` works (windows)
- [ ] README “One‑click install” section added

### Wizard
- [ ] `heidi` (no args) triggers wizard if uninitialized
- [ ] `heidi setup` works
- [ ] Tokens never printed (verified)

### Connectivity checks
- [ ] Wizard runs Copilot checks and shows PASS/FAIL
- [ ] Wizard checks OpenWebUI via API and shows PASS/FAIL
- [ ] Wizard checks Heidi `/health`
- [ ] Wizard prints OpenAPI tools URL: `http://localhost:7777/openapi.json`

### Commands
- [ ] `heidi openwebui status` works + correct exit codes
- [ ] `heidi openwebui guide` prints correct instructions

### Repo gates
- [ ] `python -m pip install -e '.[dev]'`
- [ ] `ruff check src heidi_cli/src`
- [ ] `pytest -q`
- [ ] `heidi --help`
