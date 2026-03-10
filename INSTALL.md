# 🚀 Heidi CLI One-Click Installer

Install Heidi CLI with a single command! The installer will automatically:
- Clone the latest version from GitHub
- Install all dependencies
- Build and install Heidi CLI
- Verify the installation
- Clean up temporary files

## 📋 **System Requirements**

### **Required**
- **Python 3.10+** - [Download Python](https://python.org)
- **Git** - [Download Git](https://git-scm.com)
- **pip** - Usually included with Python

### **Optional**
- **CUDA** - For GPU acceleration (automatic if available)
- **Admin/root access** - For system-wide installation (optional)

---

## 🖥️ **Installation**

### **Linux/macOS**

```bash
# Download and run the installer
curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install | bash

# Or download first, then run
wget https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install
chmod +x install
./install
```

### **Windows (PowerShell)**

```powershell
# Download and run the installer
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1" -OutFile "install.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

### **From Local Clone**

```bash
# Clone the repository
git clone https://github.com/heidi-dang/heidi-cli.git
cd heidi-cli

# Run the installer
./install  # Linux/macOS
# or
.\install.ps1  # Windows
```

---

## 🎯 **What the Installer Does**

### **✅ Automatic Steps**

1. **🔍 Check Requirements** - Verifies Python, Git, and pip
2. **📥 Clone Repository** - Downloads latest Heidi CLI from main branch
3. **🏗️ Setup Environment** - Creates virtual environment
4. **📦 Install Dependencies** - Installs all required packages
5. **🔨 Build Heidi CLI** - Compiles and builds the application
6. **⚙️ Install Heidi CLI** - Installs system-wide or for current user
7. **✅ Verify Installation** - Tests that everything works
8. **🧹 Clean Up** - Removes temporary files

### **🎉 Installation Results**

After successful installation, you'll have:
- ✅ **Heidi CLI command** available system-wide
- ✅ **All dependencies** installed and configured
- ✅ **API key system** ready to use
- ✅ **Model hosting** capabilities
- ✅ **Complete documentation** accessible

---

## 🚀 **Post-Installation**

### **Quick Start**

```bash
# Verify installation
heidi --version

# Run setup wizard
heidi setup

# Generate API key
heidi api generate --name "My First Key"

# Start model server
heidi model serve

# View help
heidi --help
```

### **Next Steps**

1. **🔑 Generate API Key**
   ```bash
   heidi api generate --name "Production Key" --user "your-username"
   ```

2. **🤖 Download Models**
   ```bash
   heidi hf search "text-generation" --limit 5
   heidi hf download "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
   ```

3. **🌐 Start API Server**
   ```bash
   heidi api server
   ```

4. **📚 Explore Documentation**
   ```bash
   # View comprehensive guide
   cat docs/how-to-use.md
   ```

---

## 🔧 **Installation Options**

### **User vs System Installation**

**User Installation (Default)**
- Installs to `~/.local/bin` (Linux/macOS) or `%USERPROFILE%\AppData\Local\Programs` (Windows)
- No admin privileges required
- Available only for current user

**System Installation (Admin Required)**
- Installs to `/usr/local/bin` (Linux/macOS) or system-wide (Windows)
- Requires admin/root privileges
- Available for all users

### **Custom Installation Path**

```bash
# Linux/macOS - set custom prefix
export HEIDI_INSTALL_PREFIX="/opt/heidi-cli"
./install

# Windows - custom path
.\install.ps1 -InstallPath "C:\HeidiCLI"
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Python Not Found**
```bash
# Install Python 3.10+
# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-pip python3-venv

# macOS (with Homebrew):
brew install python3

# Windows: Download from python.org
```

#### **Git Not Found**
```bash
# Ubuntu/Debian:
sudo apt install git

# macOS (with Homebrew):
brew install git

# Windows: Download from git-scm.com
```

#### **Permission Denied**
```bash
# Make installer executable
chmod +x install

# Or use bash directly
bash install
```

#### **Command Not Found After Installation**
```bash
# Add to PATH (Linux/macOS)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or restart your terminal
```

#### **Virtual Environment Issues**
```bash
# Clean installation
rm -rf ~/.heidi
./install --force
```

### **Get Help**

```bash
# Check system requirements
heidi doctor

# View installation logs
# Installer shows detailed error messages

# Get community help
# GitHub Issues: https://github.com/heidi-dang/heidi-cli/issues
# Discord: https://discord.gg/heidi-cli
```

---

## 📊 **Installation Verification**

### **Check Installation Status**

```bash
# Verify Heidi CLI is installed
heidi --version

# Check all systems
heidi doctor

# Test API key system
heidi api config

# List available models
heidi api models
```

### **Expected Output**

```
🔑 Heidi API Key: heidik_abc123...
📋 User Information:
┌─────────────────┬─────────────────┐
│ User ID:        │ default         │
│ Key Name:       │ Demo Key        │
│ Rate Limit:     │ 100 requests/min │
│ Usage Count:    │ 0 requests      │
└─────────────────┴─────────────────┘

🤖 Available Models:
• local://opencode-gpt-4
• hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0
• opencode://gpt-4
```

---

## 🔄 **Update Heidi CLI**

### **Update to Latest Version**

```bash
# Re-run the installer (will update existing installation)
./install

# Or manually update
pip install --upgrade heidi-cli
```

### **Uninstall Heidi CLI**

```bash
# Uninstall with pip
pip uninstall heidi-cli

# Remove configuration (optional)
rm -rf ~/.heidi
```

---

## 🎉 **Success!**

**🚀 Heidi CLI is now installed and ready to use!**

### **What You Can Do Now**

- ✅ **Generate API keys** for unified model access
- ✅ **Host models locally** with automatic management
- ✅ **Access HuggingFace models** with smart integration
- ✅ **Track usage and costs** with built-in analytics
- ✅ **Scale to production** with enterprise features

### **Learn More**

- 📖 **Complete Guide**: [docs/how-to-use.md](docs/how-to-use.md)
- 🔑 **API Keys**: [docs/api-keys.md](docs/api-keys.md)
- 🤖 **Model Management**: [docs/model-management.md](docs/model-management.md)
- 💬 **Community**: [Discord Server](https://discord.gg/heidi-cli)

---

**🎯 Installation completed successfully! Welcome to Heidi CLI!** 🚀

*Last updated: March 2026*  
*Installer version: 1.0.0*  
*Heidi CLI version: 0.1.1*
