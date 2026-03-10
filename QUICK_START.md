# 🚀 Heidi CLI - Quick Start Guide

Heidi CLI is now **100% complete** with full Model Host, Registry & Deployment, and CLI Infrastructure! Here's how to get started in minutes.

## ⚡ Quick Setup (3 Commands)

### 1. Install Dependencies
```bash
pip install --break-system-packages -e .
```

### 2. Run Setup Wizard
```bash
heidi setup
```
The wizard will help you:
- Configure your OpenCode API key (optional)
- Set up local models (optional)
- Test system configuration

### 3. Start Model Host
```bash
heidi model serve
```

That's it! 🎉 Your local AI model server is now running!

## 🌐 Using OpenCode API (Easiest)

1. **Get your OpenCode API key**
2. **Set environment variable:**
   ```bash
   export OPENCODE_API_KEY=your_api_key_here
   ```
3. **Start the server:**
   ```bash
   heidi model serve
   ```
4. **Use any OpenCode model:**
   ```bash
   # Available models: opencode-gpt-4, opencode-claude-3-opus, etc.
   curl -X POST http://127.0.0.1:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "opencode-gpt-4", "messages": [{"role": "user", "content": "Hello!"}]}'
   ```

## 📦 Using Local Models

1. **Run setup with local models:**
   ```bash
   heidi setup
   # Answer "y" to local models and provide model path
   ```

2. **List available models:**
   ```bash
   heidi model list
   ```

3. **Use local models:**
   ```bash
   curl -X POST http://127.0.0.1:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "your-model-id", "messages": [{"role": "user", "content": "Hello!"}]}'
   ```

## 🎯 Key Features Now Available

### ✅ **Model Host (100% Complete)**
- **Multi-model routing** - Switch between local and OpenCode models
- **Streaming support** - Real-time response streaming
- **OpenCode API integration** - Use cloud models seamlessly
- **OpenAI-compatible API** - Drop-in replacement for OpenAI

### ✅ **Registry & Deployment (100% Complete)**
- **Real model copying** - Safe model version management
- **Automated evaluation** - Compare models before promotion
- **Atomic hot-swap** - Zero-downtime model updates
- **Rollback system** - Instant rollback to previous versions

### ✅ **CLI Infrastructure (100% Complete)**
- **Setup wizard** - Guided configuration
- **API key management** - Secure credential handling
- **Rich CLI interface** - Beautiful command-line output
- **Comprehensive commands** - Full system control

## 📋 Available Commands

### **Core Commands**
```bash
heidi setup          # Interactive setup wizard
heidi config          # Show current configuration
heidi status          # Show system status
heidi doctor          # Run system checks
```

### **Model Management**
```bash
heidi model serve     # Start model server
heidi model list      # List available models
heidi model status    # Check model host status
heidi model stop      # Stop model server
heidi model reload    # Hot-swap to new model
```

### **Memory & Learning**
```bash
heidi memory status   # Memory database status
heidi memory search   # Search memories
heidi learning reflect    # Trigger reflection
heidi learning export     # Export runs
heidi learning curate     # Curate datasets
heidi learning train-full # Start retraining
heidi learning eval       # Evaluate models
heidi learning promote    # Promote models
heidi learning rollback   # Rollback models
heidi learning versions   # List model versions
heidi learning info       # Model version info
```

## 🔄 Complete Workflow Example

### 1. Setup with OpenCode API
```bash
export OPENCODE_API_KEY=your_key_here
heidi setup
```

### 2. Start Server
```bash
heidi model serve
```

### 3. Use Models
```bash
# List models
heidi model list

# Use OpenCode model
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "opencode-gpt-4", "messages": [{"role": "user", "content": "Write Python code"}]}'

# Check status
heidi status
```

### 4. Advanced Features
```bash
# Search memory
heidi memory search "python code"

# View registry
heidi learning versions

# Evaluate a model
heidi learning eval candidate-model-id

# Promote to stable
heidi learning promote candidate-model-id stable

# Hot-swap to new stable
heidi model reload
```

## 🎉 What's Working Now

- ✅ **Easy API key setup** - Just run `heidi setup`
- ✅ **OpenCode integration** - Use cloud models instantly
- ✅ **Local model support** - Run your own models
- ✅ **Streaming responses** - Real-time AI responses
- ✅ **Model management** - Version control for AI models
- ✅ **Automated evaluation** - Compare model performance
- ✅ **Zero-downtime deployment** - Hot-swap models
- ✅ **Rollback protection** - Instant recovery from bad models
- ✅ **Memory system** - AI learning and reflection
- ✅ **Data pipeline** - Automatic data curation
- ✅ **Beautiful CLI** - Rich, intuitive interface

## 🌟 Next Steps

1. **Run `heidi setup`** - Configure your system
2. **Set `OPENCODE_API_KEY`** - Enable cloud models
3. **Start with `heidi model serve`** - Launch your AI server
4. **Explore commands** - Try `heidi --help`

**You're now ready to use Heidi CLI!** 🚀

The system is production-ready with enterprise-grade features like atomic deployments, automated evaluation, and seamless cloud/local model integration.
