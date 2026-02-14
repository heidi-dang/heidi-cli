# Task: copilot-auth-oauth

## Goal

Replace "paste token" with OAuth login (default) for Copilot authentication.

## Changes Required

### 1. Add `heidi copilot login` command

Create new command under `copilot_app`:

```python
@copilot_app.command("login")
def copilot_login(
    use_gh: bool = typer.Option(True, "--gh/--pat", help="Use GH CLI OAuth (default) or PAT"),
    token: Optional[str] = typer.Option(None, help="PAT token (only if --pat)"),
):
```

**If `--gh` (default):**
- Check if `gh` CLI is installed (`which gh`)
- Warn if `GH_TOKEN` or `GITHUB_TOKEN` env vars are set
- Run `gh auth login` (web-based OAuth is default)
- Read token via `gh auth token`
- Store token in ConfigManager (keyring if available)

**If `--pat`:**
- Accept token via `--token` flag or prompt
- Validate it's a fine-grained PAT with Copilot scope
- Store in ConfigManager

### 2. Handle GH_TOKEN env var warning

In copilot_runtime.py `__init__`, add warning:

```python
if os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"):
    console.print("[yellow]Warning: GH_TOKEN/GITHUB_TOKEN env vars override OAuth token. Copilot may fail.[/yellow]")
```

### 3. Update `heidi copilot doctor`

- Show whether auth is via OAuth (gh) or PAT
- Show warning if env var is set
- Show clear instructions for login

### 4. Update `heidi auth gh`

- Default to device flow or guide users to `heidi copilot login`
- Keep for backward compatibility

## Acceptance Criteria

- [x] Fresh install + no token → `heidi copilot login` opens device/web flow
- [x] `heidi copilot status` shows authenticated after login (shows warning if GH_TOKEN set)
- [x] If GH_TOKEN is set, CLI prints warning
- [ ] CI path still works with PAT + Copilot Requests permission (manual test)

## Files Modified

- `heidi_cli/src/heidi_cli/cli.py` - Added `heidi copilot login` command
- `heidi_cli/src/heidi_cli/copilot_runtime.py` - Added env var warning
