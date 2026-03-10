# 🚀 Heidi CLI: Complete Step-by-Step Guide

> **Your Unified AI Model Management Platform**  
> From local model hosting to cloud AI integration - Heidi CLI does it all

---

## 📋 **Table of Contents**

1. [🔧 Quick Start](#-quick-start) - Get running in 5 minutes
2. [🏠 Setup & Configuration](#-setup--configuration) - Configure your environment
3. [🤖 Model Management](#-model-management) - Download and manage models
4. [🌐 HuggingFace Integration](#-huggingface-integration) - Access 100,000+ models
5. [💰 Token & Cost Tracking](#-token--cost-tracking) - Monitor usage and costs
6. [📊 Analytics & Monitoring](#-analytics--monitoring) - Performance insights
7. [🔧 Advanced Features](#-advanced-features) - Power user capabilities
8. [🏢 Enterprise Deployment](#-enterprise-deployment) - Production setup
9. [🛠️ Troubleshooting](#-troubleshooting) - Common issues and solutions

---

## 🚀 **Quick Start**

### **Installation**
```bash
# Install Heidi CLI
pip install heidi-cli

# Or clone from source
git clone https://github.com/heidi-dang/heidi-cli.git
cd heidi-cli
pip install -e .
```

### **First Run**
```bash
# Check installation
heidi --help

# See system status
heidi status
```

### **5-Minute Setup**
```bash
# 1. Interactive setup (recommended for new users)
heidi setup

# 2. Or quick configuration
export HEIDI_OPENCODE_API_KEY="your-api-key"
heidi config
```

---

## 🔧 **Setup & Configuration**

### **Initial Setup Wizard**
```bash
heidi setup
```
**What the wizard does:**
- ✅ **OpenCode API Configuration** - Optional cloud AI access
- ✅ **Model Paths Setup** - Configure local model storage
- ✅ **Memory & Analytics** - Enable tracking features
- ✅ **Registry Configuration** - Set up model versioning

### **Configuration File**
Your configuration is stored at: `~/.heidi/config/suite.json`

**Key Settings:**
```json
{
  "suite_enabled": true,
  "data_root": "~/.heidi",
  "model_host_enabled": true,
  "host": "127.0.0.1",
  "port": 8000,
  "models": [],
  "memory_enabled": true,
  "analytics_enabled": true
}
```

### **Environment Variables**
```bash
# OpenCode API (optional)
export HEIDI_OPENCODE_API_KEY="your-api-key"

# Custom data root
export HEIDI_STATE_ROOT="/path/to/your/data"

# CORS origins (for web interface)
export HEIDI_CORS_ORIGINS="http://localhost:3000,https://yourdomain.com"
```

---

## 🤖 **Model Management**

### **Start Model Server**
```bash
# Start local model hosting
heidi model serve

# Custom port
heidi model serve --port 8080

# Specific model
heidi model serve --model "your-model-id"
```

### **Model Status & Management**
```bash
# Check server status
heidi model status

# List available models
heidi model list

# Stop server
heidi model stop

# Reload configuration
heidi model reload
```

### **Local Model Configuration**
Add models to your configuration:

```json
{
  "models": [
    {
      "id": "local-llama",
      "path": "~/.heidi/models/llama-7b",
      "backend": "transformers",
      "device": "auto",
      "max_tokens": 2048
    }
  ]
}
```

---

## 🌐 **HuggingFace Integration**

### **Search Models**
```bash
# Basic search
heidi hf search "text generation"

# Specific task
heidi hf search "coding" --task text-generation

# Limit results
heidi hf search "llama" --limit 10

# Filter by tags
heidi hf search "chat" --task text-generation --limit 5
```

### **Model Information**
```bash
# Get detailed model info
heidi hf info "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Example output
📋 Model Info: TinyLlama/TinyLlama-1.1B-Chat-v1.0

Author: TinyLlama
Downloads: 1,994,578
Likes: 1,542
Pipeline: text-generation
Tags: transformers, safetensors, llama, text-generation, conversational
```

### **Download Models**
```bash
# Download and auto-configure
heidi hf download "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Download without configuration
heidi hf download "model-name" --add-to-config false

# Force re-download
heidi hf download "model-name" --force

# Batch download
heidi hf batch-download "model1,model2,model3"
```

### **Local Model Management**
```bash
# List downloaded models
heidi hf list-local

# Compare models
heidi hf compare "model1" "model2" "model3"

# Remove local model
heidi hf remove "model-name"

# Model usage analytics
heidi hf analytics
```

---

## 💰 **Token & Cost Tracking**

### **Usage History**
```bash
# View token usage history
heidi tokens history

# Last 10 requests
heidi tokens history --limit 10

# Specific model
heidi tokens history --model "model-name"

# Date range
heidi tokens history --from "2024-01-01" --to "2024-01-31"
```

### **Usage Summary**
```bash
# Daily summary
heidi tokens summary --period day

# Weekly summary
heidi tokens summary --period week

# Monthly summary
heidi tokens summary --period month

# Custom date range
heidi tokens summary --from "2024-01-01" --to "2024-01-07"
```

### **Cost Management**
```bash
# Configure cost per model
heidi tokens costs set "gpt-4" --input-cost 0.03 --output-cost 0.06

# List cost configurations
heidi tokens costs list

# Export cost data
heidi tokens costs export --format csv --output costs.csv

# Reset usage data (dangerous)
heidi tokens reset --confirm
```

### **Usage Statistics**
```bash
# Detailed statistics
heidi tokens stats

# Per-model breakdown
heidi tokens stats --model "model-name"

# Time-based analysis
heidi tokens stats --period week --group-by hour
```

---

## 📊 **Analytics & Monitoring**

### **Performance Analytics**
```bash
# Top models by usage
heidi analytics top-models --limit 10

# Performance metrics
heidi analytics performance --days 30

# Error rates
heidi analytics errors --period week

# Response times
heidi analytics latency --model "model-name"
```

### **System Health**
```bash
# Run comprehensive health check
heidi doctor

# Specific checks
heidi doctor --check dependencies
heidi doctor --check configuration
heidi doctor --check performance

# Continuous monitoring
heidi monitor --realtime
```

### **Export Analytics**
```bash
# Export usage data
heidi analytics export --format json --output usage.json

# Export performance metrics
heidi analytics export --metrics --format csv --output performance.csv

# Generate report
heidi analytics report --period month --output report.html
```

---

## 🔧 **Advanced Features**

### **Memory & Learning**
```bash
# Memory status
heidi memory status

# Search memory
heidi memory search "your query"

# Learning reflection
heidi learning reflect

# Export training data
heidi learning export --format jsonl

# Curate dataset
heidi learning curate --date "2024-01-01"
```

### **Registry & Versioning**
```bash
# Registry status
heidi registry status

# Model promotion
heidi registry promote --candidate "model-v2" --to-stable

# Model rollback
heidi registry rollback --to "model-v1"

# Hot-swap models
heidi registry hotswap --from "model-v1" --to "model-v2"
```

### **Batch Operations**
```bash
# Batch model download
heidi batch download --models "model1,model2,model3"

# Batch token tracking
heidi batch track --models "model1,model2" --period day

# Batch analytics
heidi batch analyze --models "all" --metrics "usage,cost,latency"
```

---

## 🏢 **Enterprise Deployment**

### **Production Server Setup**
```bash
# Production configuration
export HEIDI_ENV=production
export HEIDI_LOG_LEVEL=info
export HEIDI_MAX_WORKERS=100

# Start production server
heidi serve --host 0.0.0.0 --port 8000 --workers 10

# With SSL
heidi serve --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem
```

### **Load Balancing**
```bash
# Multiple server instances
heidi serve --port 8000 --workers 5 &
heidi serve --port 8001 --workers 5 &
heidi serve --port 8002 --workers 5 &

# Health checks
heidi cluster health --servers "localhost:8000,localhost:8001,localhost:8002"
```

### **Monitoring & Logging**
```bash
# Structured logging
export HEIDI_LOG_FORMAT=json
export HEIDI_LOG_FILE=/var/log/heidi.log

# Metrics collection
heidi metrics collect --prometheus --port 9090

# Alert configuration
heidi alerts configure --slack-webhook "https://hooks.slack.com/..." --email admin@company.com
```

### **Security Configuration**
```bash
# API rate limiting
heidi security rate-limit --requests-per-minute 100 --burst 20

# Authentication
heidi security auth --method jwt --secret "your-jwt-secret"

# CORS configuration
heidi security cors --origins "https://app.company.com" --credentials true
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Installation Problems**
```bash
# Check Python version
python --version  # Needs 3.10+

# Check dependencies
heidi doctor --check dependencies

# Clean installation
pip uninstall heidi-cli && pip install heidi-cli
```

#### **Model Loading Issues**
```bash
# Check model paths
heidi model status --verbose

# Validate model files
heidi model validate --path "path/to/model"

# Clear cache
heidi cache clear --models
```

#### **Performance Issues**
```bash
# Check system resources
heidi doctor --check performance

# Monitor memory usage
heidi monitor --memory --realtime

# Profile requests
heidi profile --requests --duration 60
```

#### **Network Issues**
```bash
# Test API connectivity
heidi test --api opencode

# Check HuggingFace access
heidi test --huggingface

# Debug network issues
heidi debug --network --verbose
```

### **Getting Help**
```bash
# General help
heidi --help

# Command-specific help
heidi model --help
heidi hf --help
heidi tokens --help

# Doctor for diagnostics
heidi doctor --verbose

# Version information
heidi --version
```

### **Community Support**
```bash
# Report issues
heidi report issue --title "Problem description"

# Request features
heidi request feature --description "Feature request"

# Community forum
heidi community --open
```

---

## 🎯 **Best Practices**

### **For Beginners**
1. **Start with setup wizard**: `heidi setup`
2. **Use HuggingFace integration**: Easy model discovery
3. **Monitor usage**: `heidi tokens summary` regularly
4. **Check health**: `heidi doctor` when issues occur

### **For Power Users**
1. **Configure cost tracking**: Set up pricing for budget management
2. **Use batch operations**: Efficient bulk operations
3. **Enable analytics**: Deep insights into usage patterns
4. **Custom configuration**: Optimize for your workflow

### **For Enterprises**
1. **Production deployment**: Use environment variables
2. **Load balancing**: Multiple server instances
3. **Monitoring**: Comprehensive logging and metrics
4. **Security**: Rate limiting and authentication

### **Performance Tips**
1. **Local models**: Faster response, no internet required
2. **Cloud models**: Latest capabilities, no hardware limits
3. **Hybrid approach**: Use local for speed, cloud for capabilities
4. **Regular monitoring**: Track costs and performance

---

## 📚 **Additional Resources**

### **Documentation**
- **API Reference**: `https://github.com/heidi-dang/heidi-cli/blob/main/docs/api.md`
- **Configuration Guide**: `https://github.com/heidi-dang/heidi-cli/blob/main/docs/config.md`
- **Troubleshooting Guide**: `https://github.com/heidi-dang/heidi-cli/blob/main/docs/troubleshooting.md`

### **Community**
- **GitHub Repository**: `https://github.com/heidi-dang/heidi-cli`
- **Discord Community**: `https://discord.gg/heidi-cli`
- **Issue Tracker**: `https://github.com/heidi-dang/heidi-cli/issues`

### **Tutorials**
- **Video Tutorial**: `https://www.youtube.com/watch?v=heidi-cli-tutorial`
- **Blog Posts**: `https://blog.heidi-cli.com`
- **Examples Repository**: `https://github.com/heidi-dang/heidi-cli-examples`

---

## 🚀 **Quick Reference Card**

```bash
# Essential Commands Cheat Sheet
heidi setup              # Initial setup wizard
heidi status             # System status overview
heidi model serve         # Start model server
heidi hf search "query"  # Search HuggingFace models
heidi hf download "model" # Download model
heidi tokens summary       # View usage costs
heidi doctor             # Health check
heidi --help              # Get help

# Advanced Commands
heidi analytics top-models    # Performance analytics
heidi registry promote        # Model versioning
heidi batch download          # Bulk operations
heidi monitor --realtime      # Live monitoring
```

---

**🎉 Congratulations! You're now ready to unlock the full power of Heidi CLI!**

> **From your first model download to enterprise deployment, Heidi CLI scales with your needs.**

**Need help?** Visit `https://github.com/heidi-dang/heidi-cli/issues` or join our Discord community!

---

*Last updated: March 2026*  
*Documentation version: 1.0*  
*Heidi CLI version: 0.1.1*
