# 🚀 1-Click Install + Interactive Setup Wizard + OpenWebUI Integration

This PR delivers the complete setup wizard and installation system for Heidi CLI, making it incredibly easy for new users to get started with zero friction.

## ✨ **What This PR Delivers**

### **1️⃣ One-Click Installation**
- **`install.sh`** - Linux/macOS installation with automatic pipx setup
- **`install.ps1`** - Windows PowerShell installation with Python launcher verification
- Both scripts install Heidi CLI directly from GitHub repository

### **2️⃣ Interactive Setup Wizard (7 Steps)**
When users run `heidi` for the first time, they get a beautiful 7-step interactive wizard:

1. **Environment Checks** - Verifies Python, directories, and server setup
2. **Initialize Project** - Creates `.heidi/` directory with proper permissions
3. **GitHub/Copilot Setup** - Secure token input with authentication testing
4. **OpenWebUI Setup** - URL configuration with API connectivity testing
5. **Heidi Server Health** - Automatic server startup and verification
6. **OpenWebUI Tools Guide** - Exact URLs and configuration steps
7. **Final Summary** - Complete status overview with next steps

### **3️⃣ OpenWebUI Integration Commands**
- **`heidi openwebui status`** - Check connectivity with proper exit codes
- **`heidi openwebui guide`** - Print exact setup instructions
- **`heidi openwebui configure`** - Configure settings interactively

### **4️⃣ Security & Best Practices**
- ✅ **Tokens never printed** - All secrets handled securely
- ✅ **Proper file permissions** - Secrets file set to 0600
- ✅ **Git ignore protection** - `.heidi/` automatically ignored
- ✅ **No sensitive data logged** - Professional security standards

## 🚀 **Zero-Friction User Experience**

**For new users:**
```bash
# Linux/macOS
curl -sSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.sh | bash
heidi  # Automatically starts beautiful setup wizard

# Windows
irm https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1 | iex
heidi  # Automatically starts beautiful setup wizard
```

## 📋 **Implementation Details**

### **New Files Added:**
- `install.sh` - Linux/macOS one-click installer
- `install.ps1` - Windows PowerShell installer  
- `heidi_cli/src/heidi_cli/setup_wizard.py` - Complete 7-step wizard
- `heidi_cli/src/heidi_cli/openwebui_commands.py` - OpenWebUI commands

### **Files Modified:**
- `heidi_cli/src/heidi_cli/cli.py` - Automatic wizard launch + setup command
- `heidi_cli/src/heidi_cli/config.py` - OpenWebUI configuration support
- `heidi_cli/pyproject.toml` - Added httpx dependency
- `.gitignore` - Added `.heidi/` protection
- `README.md` - Updated with one-click install docs

### **Key Features:**
- **Rich UI** - Beautiful panels, tables, and progress indicators
- **Error Handling** - Comprehensive validation and helpful messages
- **Exit Codes** - Proper exit codes for scripting
- **Backward Compatibility** - All existing commands preserved

## ✅ **All Requirements Met**

From the implementation specifications:

### **Install Scripts**
- ✅ `install.sh` works (Linux/macOS) - pipx installation, GitHub repo install
- ✅ `install.ps1` works (Windows) - py launcher verification, pipx setup
- ✅ README "One-click install" section added - with exact commands

### **Wizard Implementation**  
- ✅ `heidi` (no args) triggers wizard if uninitialized - automatic launch
- ✅ `heidi setup` works - explicit command for wizard
- ✅ Tokens never printed (verified) - all secrets handled securely

### **Connectivity Checks**
- ✅ Wizard runs Copilot checks and shows PASS/FAIL - auth status + doctor
- ✅ Wizard checks OpenWebUI via API and shows PASS/FAIL - `/api/models` endpoint
- ✅ Wizard checks Heidi `/health` - server startup and verification
- ✅ Wizard prints OpenAPI tools URL: `http://localhost:7777/openapi.json`

### **Commands**
- ✅ `heidi openwebui status` works + correct exit codes - 0/1/2/3
- ✅ `heidi openwebui guide` prints correct instructions - exact URLs

### **Non-negotiables Met**
- ✅ **Never print tokens/secrets** - All password inputs hidden
- ✅ **Project-local state** - Everything in `./.heidi/` as specified  
- ✅ **Terminal-first** - No VS Code dependency
- ✅ **Minimal changes** - Only added new functionality

## 🧪 **Testing & Validation**

The implementation has been thoroughly validated for:
- ✅ Automatic wizard launch on first run
- ✅ All 7 wizard steps complete successfully
- ✅ OpenWebUI connectivity testing
- ✅ Proper exit codes for status command
- ✅ Security (no token leakage)
- ✅ Error handling and edge cases

## 🎉 **Ready for Production**

This PR delivers a professional, user-friendly onboarding experience that guides new users through the complete setup process while maintaining all existing functionality for power users.

**Branch**: `feat/setup-wizard`  
**Status**: ✅ Ready for merge  
**PR URL**: https://github.com/heidi-dang/heidi-cli/pull/new/feat/setup-wizard

---

**Next step**: Review and merge to provide users with the seamless Heidi CLI experience they deserve! 🚀