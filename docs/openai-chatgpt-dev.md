# openai-chatgpt-dev.md — ChatGPT Plus/Pro OAuth (MUST WORK) Plan

> Goal: Let a user use their existing **ChatGPT Plus/Pro** subscription (no separate OpenAI API credits) by authenticating through an **official OAuth flow** and then using OpenCode as the execution provider.

This plan is designed around:
- **OpenCode** storing auth/session data in `~/.local/share/opencode/auth.json` (Windows: `%USERPROFILE%\.local\share\opencode\auth.json`).  
  Sources: https://opencode.ai/docs/providers/ • https://opencode.ai/docs/troubleshooting/
- OpenAI **Codex** supporting **ChatGPT OAuth / device auth / API key** via `codex login` (and `codex login --device-auth` for headless).  
  Sources: https://developers.openai.com/codex/cli/reference/ • https://developers.openai.com/codex/auth/
- The OpenCode ecosystem plugin **opencode-openai-codex-auth** that explicitly targets ChatGPT Plus/Pro OAuth and provides model presets.  
  Source: https://opencode.ai/docs/ecosystem/ → `opencode-openai-codex-auth` (GitHub)

---

## Non‑negotiable requirements (Definition of Done)

### MUST WORK (User experience)
1. User can connect by running one command or pressing one button:
   - CLI: `heidi connect opencode openai`
   - UI: “Connect OpenAI (ChatGPT Plus/Pro)”
2. Browser OAuth flow completes and returns “Authentication Successful”.
3. Credentials are stored locally by OpenCode:
   - macOS/Linux: `~/.local/share/opencode/auth.json`
   - Windows: `%USERPROFILE%\.local\share\opencode\auth.json`  
   (Do **not** log secrets.)
4. Heidi can verify the connection:
   - `heidi connect status` shows: `OpenCode: OpenAI (ChatGPT Plus/Pro) CONNECTED`
5. Heidi can run a real command through OpenCode using a subscription model:
   - `opencode models openai` returns at least one OpenAI model
   - `opencode run ... --model=openai/<something>` succeeds

### MUST NOT DO (Safety / compliance)
- Never scrape browser cookies or steal tokens.
- Never print the token content of `auth.json`.
- Never store OAuth tokens in the project repo.
- This subscription OAuth path is for **personal development use**. For production or multi-user systems, use OpenAI Platform API.  
  (The plugin itself warns about this in its README.)

---

## Architecture (high level)

**Heidi CLI / Server** does not implement OpenAI OAuth itself.  
It *delegates* subscription auth to OpenCode, which uses an official authentication method (Codex OAuth-style) via the OpenCode provider/plugin.

Flow:
1) Heidi triggers OpenCode auth install/config (plugin + config).
2) Heidi triggers OpenCode login (opens browser).
3) OpenCode stores tokens in `~/.local/share/opencode/auth.json`.
4) Heidi verifies models and can run tasks through OpenCode.

---

## Phase 0 — Prereqs & invariants

### Prereqs to check (Heidi CLI must validate)
- `opencode` is installed and runnable (`opencode --version`).
- `node`/`npx` is available (plugin quick start uses `npx`).
- User is on a plan that includes Codex/ChatGPT OAuth access (Plus/Pro/Business/Edu/Enterprise).  
  Source: https://developers.openai.com/codex/cli/

### Storage invariants
- Heidi stores its own config in global Heidi config home (HEIDI_HOME / OS dirs).
- OpenCode stores auth in OpenCode storage dir:
  - `~/.local/share/opencode/auth.json`  
    Source: https://opencode.ai/docs/providers/
  - Windows path in troubleshooting docs.  
    Source: https://opencode.ai/docs/troubleshooting/

---

## Phase 1 — “One command connect” (CLI) (MUST)

### New/confirmed command
- `heidi connect opencode openai`

### What this command must do
1) **Install/ensure OpenCode plugin presets**
   - Use the plugin’s “one install” command:
     ```bash
     npx -y opencode-openai-codex-auth@latest
     ```
   - Source (plugin README): https://github.com/numman-ali/opencode-openai-codex-auth
2) **Launch OpenCode login**
   - Run:
     ```bash
     opencode auth login
     ```
   - Source: https://opencode.ai/docs/cli/  (login)
3) **Wait for success**
   - Heidi should:
     - detect the OpenCode process exit code
     - then verify `auth.json` exists and contains an OpenAI entry (without printing secrets)
4) **Verify models**
   - Run:
     ```bash
     opencode models openai
     ```
   - Source: https://opencode.ai/docs/cli/  (models)
5) **Run a tiny test request**
   - Example (from plugin README):
     ```bash
     opencode run "write hello world to test.txt" --model=openai/gpt-5.2 --variant=medium
     ```
   - If the model name differs (version drift), choose the first returned by `opencode models openai`.
   - Source (plugin README): https://github.com/numman-ali/opencode-openai-codex-auth

### CLI acceptance output (exact)
- After success:
  - `Connected: OpenCode → OpenAI (ChatGPT Plus/Pro)`
  - `Auth file: <path>`
  - `Models: <count> (first: openai/<model>)`
  - `Test run: PASS`

### Fail-fast behaviors
- If `opencode` missing → print install instructions and stop.
- If `npx` missing → print “Install Node.js” instructions and stop.
- If auth fails → print the exact next step:
  - “Try headless fallback: `codex login --device-auth`”  
    Source: https://developers.openai.com/codex/auth/
  - Or “Run `opencode --log-level DEBUG` and check OpenCode logs dir”  
    Source: https://opencode.ai/docs/troubleshooting/

---

## Phase 2 — UI support (heidi-cli-ui) (MUST)

### UI screen: “Connections → OpenAI (ChatGPT Plus/Pro)”
Provide:
- **Connect** button
- **Verify** button
- **Troubleshooting** section

#### Connect button (minimum viable, guaranteed to work)
Because OpenCode login is interactive and may open a browser, the safest MVP is:
- UI shows **copy/paste** commands in a modal (one-click copy):
  1) `npx -y opencode-openai-codex-auth@latest`
  2) `opencode auth login`
  3) `opencode models openai`
- UI then prompts user to press **Verify**.

This is “built-in OAuth system” in the sense that the product integrates OpenCode’s official OAuth login, without requiring API credits.

#### Verify button (must be fully automated)
- Calls heidi backend:
  - `GET /connect/opencode/openai/status`
- Backend returns:
  - `connected: true|false`
  - `authPath: ...`
  - `models: [...]` (names only)
  - `lastError: ...` (safe string, no secrets)

---

## Phase 3 — Backend endpoints needed for UI

Add endpoints to heidi-cli server:

1) `GET /connect/opencode/openai/status`
- Checks:
  - OpenCode storage dir exists (OS-aware path)
  - `auth.json` exists
  - `opencode models openai` returns models
- Returns JSON for UI.

2) `POST /connect/opencode/openai/test`
- Runs a tiny test request:
  - `opencode run "say ok" --model=openai/<first_model>`
- Returns:
  - `pass/fail`, `run_output_tail` (trimmed), no tokens.

> Note: OpenCode storage path + logs path are documented.  
> Source: https://opencode.ai/docs/troubleshooting/

---

## Phase 4 — Headless / remote environments (MUST have a solution)

Browser OAuth can fail on servers/headless machines. OpenAI recommends **device code** auth for Codex:
- `codex login --device-auth`  
  Sources: https://developers.openai.com/codex/auth/ • https://developers.openai.com/codex/cli/reference/

### Required guidance (shown on failure)
If `opencode auth login` fails due to headless callback:
1) Try device code via Codex:
   ```bash
   codex login --device-auth
   ```
2) If login works on a laptop but not on server:
   - OpenAI documents copying `~/.codex/auth.json` for headless fallback (treat like password).  
     Source: https://developers.openai.com/codex/auth/

**Important:** This fallback is for Codex CLI. OpenCode may still require its own auth store; use this as the official headless route and document it clearly in the UI/CLI.

---

## Phase 5 — Security controls (MUST)

### Treat credentials like passwords
- OpenCode: `auth.json` contains “Authentication data like API keys, OAuth tokens”  
  Source: https://opencode.ai/docs/troubleshooting/
- OpenAI warns `~/.codex/auth.json` contains access tokens and must be treated like a password.  
  Source: https://developers.openai.com/codex/auth/

### Implementation rules
- Never print `auth.json` contents.
- Never commit it, never upload it to issues/tickets.
- If you need to show “connected”, show only:
  - provider name, timestamp, and masked identifier.

---

## Phase 6 — Automated test plan (MUST PASS)

### Local interactive (GUI machine)
1) `heidi connect opencode openai`
2) Browser opens → user authenticates
3) Heidi runs:
   - `opencode models openai`  → must return ≥ 1 model
   - `opencode run "say ok" --model=openai/<model>` → must succeed
4) `heidi connect status` shows connected

### UI verification
1) Open Heidi UI → Connections
2) Click “Verify” → shows connected + models
3) Click “Test” → PASS

### Regression tests
- With OpenCode uninstalled → clear failure message
- With Node missing → clear failure message
- With corrupted OpenCode store:
  - docs recommend clearing `~/.local/share/opencode`  
    Source: https://opencode.ai/docs/troubleshooting/

---

## Phase 7 — Launch checklist (copy/paste)

- [ ] `heidi connect opencode openai` works on macOS + Windows + Linux (at least one each)
- [ ] UI shows Connect instructions + Verify works
- [ ] `opencode models openai` returns models
- [ ] OpenCode auth stored in correct path per OS
- [ ] No secrets printed in logs
- [ ] Troubleshooting doc exists in both repos

---

## Troubleshooting (what support should ask first)

1) Are you on a GUI machine? If headless, use `codex login --device-auth`  
   Source: https://developers.openai.com/codex/auth/
2) Does OpenCode see providers?
   - `opencode models`
   - `opencode --log-level DEBUG` and check logs dir  
     Source: https://opencode.ai/docs/troubleshooting/
3) Is OpenCode storage present?
   - macOS/Linux: `~/.local/share/opencode/`
   - Windows: `%USERPROFILE%\.local\share\opencode`  
     Source: https://opencode.ai/docs/troubleshooting/

---

## Notes (keep expectations honest)
- Model availability depends on plan and current offerings. Always verify via `opencode models openai`.
- This path is for **personal subscription usage** through official OAuth; not for multi-user resale or production API workloads.
