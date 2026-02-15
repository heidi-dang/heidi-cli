# memory.md — Heidi CLI + Heidi UI (current state + decisions)

## Project snapshot
You’re building **Heidi CLI**: a **terminal-first orchestrator** with a strict gated loop:
**Plan → Runner → Reviewer-Audit → Self-Audit → PASS/FAIL** (max retries).
Repo artifacts must be written every run:
- `tasks/<slug>.md`
- `tasks/<slug>.audit.md`

Phases 0–3 must work without any VS Code dashboard dependency. Security is non-negotiable: redact tokens, no secrets in browser UI, secrets file permissions `0600` on Unix, no junk committed.

---

## Canonical defaults (must stay consistent)
- **Heidi backend**: `http://127.0.0.1:7777`
- **Heidi UI**: `http://127.0.0.1:3002` (strict port; fail if busy)
- OpenWebUI is a separate service and may use **3000** (do not treat as Heidi UI).

---

## Global config + project artifacts separation (core rule)
### Global config home (never relative)
Central resolver priority:
1) `HEIDI_HOME` override
2) OS defaults:
   - Linux: `~/.config/heidi`
   - macOS: `~/Library/Application Support/Heidi`
   - Windows: `%APPDATA%\Heidi`

Optional global dirs (recommended):
- State (Linux): `~/.local/state/heidi`
- Cache (Linux): `~/.cache/heidi`

### Project artifacts stay in project root
- Tasks always go to `<project_root>/tasks`
- Project root is detected via git root when possible; else CWD fallback
- Do not put secrets or runtime state in the project directory by default

### `heidi paths` command
Must print absolute:
- Config (global)
- State (global)
- Cache (global)
- Project Root
- Tasks (project)

Legacy handling:
- Detect `./.heidi/` and warn with: “Run `heidi migrate` to move config”

Secrets:
- Stored in global config, **0600 perms** on Unix (example: `-rw-------`)

User preference captured:
- When you ask for a plan, you want **only the actionable dev plan** (no extra explanations).

---

## Installer (`install.sh`) requirements (one-click)
Primary requirement: **installer must not write `./.heidi`** (no CWD pollution).
Installer installs CLI and may set up UI clone, but must keep config/state global.

### Terminal safety (fix “can’t type / invisible typing”)
- Save/restore terminal mode using `stty` and `trap`
- Disable XON/XOFF during install: `stty -ixon`
- Read prompts from `/dev/tty` (because `curl | bash` stdin is a pipe)
- Restore cursor/echo on EXIT/INT/TERM

### Deterministic global dirs (CI stability)
CI kept failing because it expected global config dir after install.
Permanent fix: **installer should create empty global dirs** (no secrets):
- Linux: create `${XDG_CONFIG_HOME:-$HOME/.config}/heidi`, `${XDG_STATE_HOME:-$HOME/.local/state}/heidi`, `${XDG_CACHE_HOME:-$HOME/.cache}/heidi`
- macOS: `~/Library/Application Support/Heidi` + `~/Library/Caches/Heidi`
- If `HEIDI_HOME` set: ensure it exists

### UI cloning/update behavior in installer
UI should be cloned/updated in a deterministic global location:
- If `HEIDI_HOME` set: `$HEIDI_HOME/ui`
- Else: `${XDG_CACHE_HOME:-$HOME/.cache}/heidi/ui`
Rules:
- If exists: `git pull --ff-only`
- If missing: `git clone --depth 1 https://github.com/heidi-dang/heidi-cli-ui.git <ui_dir>`
- Never clone UI into CWD implicitly

---

## UI repo (heidi-cli-ui) contract with Heidi CLI (no need to read heidi-cli repo)
### Vite server
- `host: "127.0.0.1"`
- `port: 3002`
- `strictPort: true`

### Backend base env rules (must match CLI)
UI base resolution order:
1) `VITE_HEIDI_SERVER_BASE`
2) `HEIDI_SERVER_BASE`
3) default `http://127.0.0.1:7777`

Implementation note:
- Use `loadEnv()` in `vite.config.ts` (more reliable than `process.env` alone)

### API path style
Frontend must call **only** `/api/*`:
- `/api/health`
- `/api/run`
- `/api/loop`
- `/api/runs`
- `/api/runs/:id`
- `/api/runs/:id/stream`

No mixed direct `/health` calls and no hardcoded `localhost:7777`.
`src/api/heidi.ts` should default to relative base: `DEFAULT_BASE_URL="/api"`.

### Proxy
- Proxy `/api/*` → `${backend_base}/*` (strip `/api`)
- Backend base must be env-driven as above

### UX
- On app load: call `/api/health`
- If unreachable: show a clear banner “Backend not reachable” + Retry button
- Streaming: prefer SSE (`/api/runs/:id/stream`), fallback to polling (`/api/runs/:id`)

### Workflow constraint
UI dev may push directly to `main` (no PR). Safety process:
- `git checkout main && git pull --ff-only`
- apply changes
- `npm ci && npm run build`
- commit + push

---

## Env standardization (who owns what)
Canonical meaning:
- `HEIDI_SERVER_BASE` = canonical backend base for CLI/backend/docs
- `VITE_HEIDI_SERVER_BASE` = UI-visible equivalent (Vite requirement)

Rules:
- UI reads in order: `VITE_HEIDI_SERVER_BASE` → `HEIDI_SERVER_BASE` → default
- CLI should export **both** when spawning UI so it works everywhere

Ownership:
- UI dev: implements env priority + proxy + `/api/*` consistency + `.env.example`
- Heidi-cli Dev1: sets env vars when launching UI
- Heidi-cli Dev2: avoid introducing new env names in update/upgrade flows

---

## Copilot auth direction
Instead of asking users to paste tokens by default:
- Prefer GitHub CLI OAuth device/browser flow:
  - `gh auth login`
  - `gh auth token` used by Heidi for requests
- Keep PAT as fallback for headless/CI
Key gotchas:
- Missing Copilot permission leads to “auth OK but Copilot fails”
- `GH_TOKEN` / `GITHUB_TOKEN` env vars can override `gh` stored creds; warn clearly

Follow-up issues to ensure are handled:
- If `gh` missing → fallback to PAT mode
- Token env var naming must be consistent across code + docs
- Add tests for auth flow and error parsing

---

## user-registration branch (auth impacts UI streaming)
Auth is where UI compatibility can break:
- `EventSource` cannot send custom headers, so **header-based auth can break SSE**
Safe approaches:
1) Cookie-based auth (best): cookies automatically flow to SSE via same-origin proxy
2) Header token auth: disable SSE and rely on polling fallback, or switch streaming to `fetch()` streaming, or allow query token (less ideal)

Checklist for “UI still works with auth”:
- Existing endpoints must remain functional: `/health`, `/run`, `/loop`, `/runs`, `/runs/:id`, `/runs/:id/stream`
- UI must handle 401/403 differently from “offline” (show unauthorized/login required)

Workflow rule:
- Keep `user-registration` synced with latest `main` (rebase/merge) before building on it, to avoid drifting ports/env/proxy behavior.

---

## Dev assignments (current)
### Dev1 (Heidi CLI core/launcher/auth)
- Ensure ports printed and defaults are consistent (UI 3002, backend 7777)
- Ensure `heidi start ui` appears in `--help`
- Ensure CLI → UI env exports: both `VITE_HEIDI_SERVER_BASE` and `HEIDI_SERVER_BASE`
- Copilot auth hardening + tests (gh missing fallback, env var precedence, error messages)

### Dev2 (Heidi CLI connections)
Merged: **PR #15** (connect commands) delivered:
- `heidi connect status`
- `heidi connect ollama`
- `heidi connect opencode`
- `heidi connect disconnect`
Features:
- `--json`
- `--save/--no-save`
- `--yes/-y` confirmations
- config stored globally; secrets stored with `0600`
CI reported passing: tests, lint, acceptance, clean-release, installer-no-cwd, safety, secrets

### UI dev (heidi-cli-ui + UI backend pieces)
Implement and push-to-main:
- Vite port 3002 strict
- Env priority via loadEnv
- `/api/*` everywhere, DEFAULT_BASE_URL="/api"
- Connectivity banner in App.tsx
- `.env.example` + README updates

---

## CI failure that appeared + permanent fix
Failure: “Global config not created at /home/runner/.config/heidi”
Cause: installer didn’t create global dirs during install.
Permanent fix: installer should `mkdir -p` global config/state/cache dirs (empty), respecting `HEIDI_HOME`/XDG/macOS paths.

---

## Release gate (must pass before calling it done)
- `curl … | bash` from a temp dir:
  - does not create `./.heidi`
  - does create global config dir(s)
  - terminal remains usable afterward
- `heidi paths` shows absolute global dirs + project root + tasks
- UI starts on `127.0.0.1:3002` with strictPort
- UI calls `/api/health` successfully when backend on 7777
- Changing `VITE_HEIDI_SERVER_BASE` re-points UI without code edits
- Tasks always written to `<project_root>/tasks`
- Secrets always global, Unix perms 0600, never printed

