# 🚀 Quick Installation Guide

## **One-Click Install (Recommended)**

### **Linux/macOS**
```bash
curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install | bash
```

### **Windows (PowerShell)**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1" -OutFile "install.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

---

## **🔧 If "heidi command not found" After Installation**

### **Solution 1: Update PATH (Linux/macOS)**
```bash
# Add to current session
export PATH="$HOME/.local/bin:$PATH"

# Add permanently to bashrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Test installation
heidi --version
```

### **Solution 2: Update PATH (Windows)**
```powershell
# Add to current session
$env:PATH = "$env:USERPROFILE\.local\bin;" + $env:PATH

# Add permanently
[Environment]::SetEnvironmentVariable("PATH", $env:USERPROFILE\.local\bin + ";" + $env:PATH, "User")

# Test installation
heidi --version
```

### **Solution 3: Restart Terminal**
Sometimes you just need to restart your terminal session for the PATH changes to take effect.

---

## **📋 Manual Installation (If Installer Fails)**

### **Step 1: Clone Repository**
```bash
git clone https://github.com/heidi-dang/heidi-cli.git
cd heidi-cli
```

### **Step 2: Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\Activate.ps1  # Windows
```

### **Step 3: Install Dependencies**
```bash
pip install build setuptools wheel
pip install -e .
```

### **Step 4: Verify Installation**
```bash
# Test if package can be imported
python -c "import heidi_cli; print('Package installed successfully')"

# Test command (may need PATH update)
heidi --version
```

### **Step 5: Update PATH if Needed**
```bash
# Find where heidi was installed
find $HOME/.local -name "heidi" 2>/dev/null
# or
find /usr/local -name "heidi" 2>/dev/null

# Add the directory to PATH
export PATH="/path/to/heidi/directory:$PATH"
```

---

## **🎯 Quick Start After Installation**

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

---

## **🛠️ Troubleshooting**

### **Common Issues**

#### **"python: command not found"**
```bash
# Install Python 3.10+
# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-pip python3-venv

# macOS (with Homebrew):
brew install python3
```

#### **"pip: command not found"**
```bash
# Install pip
python3 -m ensurepip --upgrade
# or
sudo apt install python3-pip
```

#### **"git: command not found"**
```bash
# Install git
# Ubuntu/Debian:
sudo apt install git

# macOS (with Homebrew):
brew install git
```

#### **"Permission denied"**
```bash
# Make installer executable
chmod +x install

# Or run with bash directly
bash install
```

#### **Virtual environment issues**
```bash
# Clean installation
rm -rf ~/.heidi
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
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

## **🎉 Success!**

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
