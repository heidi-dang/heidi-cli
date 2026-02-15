# ✨ 1-Click Install + Interactive Setup Wizard + OpenWebUI Integration

This PR implements the complete setup wizard and installation system for Heidi CLI, making it incredibly easy for new users to get started.

## 🎯 What This PR Delivers

### 1️⃣ **One-Click Installation Scripts**
- **`install.sh`** - Linux/macOS installation with automatic pipx setup
- **`install.ps1`** - Windows PowerShell installation with Python launcher verification
- Both scripts install Heidi CLI directly from the GitHub repository

### 2️⃣ **Interactive Setup Wizard**
When users run `heidi` for the first time, they get a beautiful 7-step interactive wizard:

1. **Environment Checks** - Verifies Python, directories, and server setup
2. **Initialize Project State** - Creates `.heidi/` directory with proper permissions
3. **GitHub/Copilot Setup** - Secure token input with authentication testing
4. **OpenWebUI Setup** - URL configuration with API connectivity testing
5. **Heidi Server Health Check** - Automatic server startup and verification
6. **OpenWebUI Tools Connection Guide** - Exact URLs and configuration steps
7. **Final Summary** - Complete status overview with next steps

### 3️⃣ **OpenWebUI Integration Commands**
- **`heidi openwebui status`** - Check connectivity with proper exit codes
- **`heidi openwebui guide`** - Print exact setup instructions
- **`heidi openwebui configure`** - Configure settings interactively

### 4️⃣ **Security & Best Practices**
- ✅ **Tokens never printed** - All secrets are handled securely
- ✅ **Proper file permissions** - Secrets file set to 0600
- ✅ **Git ignore protection** - `.heidi/` automatically ignored
- ✅ **Project-local state** - Everything stays in `./.heidi/` as specified

## 🚀 Quick Start for New Users

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash
heidi  # Automatically starts setup wizard
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1 | iex
heidi  # Automatically starts setup wizard
```

## 📋 Implementation Details

### Files Added/Modified:
- `install.sh` - Linux/macOS one-click installer
- `install.ps1` - Windows PowerShell installer  
- `heidi_cli/src/heidi_cli/setup_wizard.py` - Complete 7-step wizard
- `heidi_cli/src/heidi_cli/openwebui_commands.py` - OpenWebUI commands
- `heidi_cli/src/heidi_cli/cli.py` - Automatic wizard launch + setup command
- `heidi_cli/src/heidi_cli/config.py` - OpenWebUI configuration support
- `.gitignore` - Added `.heidi/` protection
- `README.md` - Updated with one-click install docs

### Key Features:
- **Rich UI** - Beautiful panels, tables, and progress indicators
- **Error Handling** - Comprehensive validation and helpful error messages
- **Exit Codes** - Proper exit codes for scripting (`heidi openwebui status`)
- **Backward Compatibility** - All existing commands work unchanged

## ✅ Definition of Done - All Requirements Met

From the todo specifications:

### Install Scripts
- ✅ `install.sh` works (mac/linux) - pipx installation, GitHub repo install
- ✅ `install.ps1` works (windows) - py launcher verification, pipx setup
- ✅ README "One-click install" section added - with exact commands

### Wizard Implementation  
- ✅ `heidi` (no args) triggers wizard if uninitialized - automatic launch
- ✅ `heidi setup` works - explicit command for wizard
- ✅ Tokens never printed (verified) - all secrets handled securely

### Connectivity Checks
- ✅ Wizard runs Copilot checks and shows PASS/FAIL - auth status + doctor
- ✅ Wizard checks OpenWebUI via API and shows PASS/FAIL - /api/models endpoint
- ✅ Wizard checks Heidi `/health` - server startup and verification
- ✅ Wizard prints OpenAPI tools URL: `http://localhost:7777/openapi.json`

### Commands
- ✅ `heidi openwebui status` works + correct exit codes - 0/1/2/3
- ✅ `heidi openwebui guide` prints correct instructions - exact URLs

### Non-negotiables Met
- ✅ **Never print tokens/secrets** - All password inputs hidden
- ✅ **Project-local state** - Everything in `./.heidi/` as specified  
- ✅ **Terminal-first** - No VS Code dependency
- ✅ **Minimal changes** - Only added new functionality

## 🧪 Testing

The implementation has been thoroughly tested for:
- ✅ Automatic wizard launch on first run
- ✅ All 7 wizard steps complete successfully
- ✅ OpenWebUI connectivity testing
- ✅ Proper exit codes for status command
- ✅ Security (no token leakage)
- ✅ Error handling and edge cases

## 🎉 Ready for Merge

This PR delivers a complete, production-ready setup experience that makes Heidi CLI accessible to users of all skill levels. The implementation follows all specifications exactly and maintains backward compatibility.

**Next step:** Review and merge to provide the seamless onboarding experience! 🚀