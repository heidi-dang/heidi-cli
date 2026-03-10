# Heidi CLI: The "Brain" for Your Local AI

[![One-Click Install](https://img.shields.io/badge/Install-One%20Click-blue?style=for-the-badge&logo=linux)](https://github.com/heidi-dang/heidi-cli#-one-click-installation) [![API Keys](https://img.shields.io/badge/API%20Keys-Unified%20Access-green?style=for-the-badge&logo=api)](https://github.com/heidi-dang/heidi-cli/blob/main/docs/api-keys.md) [![Documentation](https://img.shields.io/badge/Docs-Complete%20Guide-purple?style=for-the-badge&logo=readthedocs)](https://github.com/heidi-dang/heidi-cli/blob/main/docs/how-to-use.md)

Listen, we've all been there. You've got a shiny new LLM running on your laptop, but it's basically a goldfish. It forgets what it did five minutes ago, and it keeps making the same dumb mistakes. 

Enter **Heidi CLI**. 

Heidi is a command-center for a **Unified Learning Suite**. It's not just some fancy wrapper for an API; it's a full-on "Closed-Loop Learning System." Basically, it's a way to turn those generic AI models into specialized, self-improving agents that actually learn from their own successes and failures. It's like a personal trainer, but for your LLMs.

---

## 🚀 **One-Click Installation**

Install Heidi CLI with a single command! The installer will automatically:
- Clone the latest version from GitHub
- Install all dependencies
- Build and install Heidi CLI
- Verify the installation

### **Linux/macOS**
```bash
# Quick install (one command)
curl -fsSL https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install | bash

# Or download first
wget https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install
chmod +x install
./install
```

### **Windows (PowerShell)**
```powershell
# Download and run
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/heidi-dang/heidi-cli/main/install.ps1" -OutFile "install.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

### **After Installation**
```bash
# Verify installation
heidi --version

# Quick start
heidi setup
heidi api generate --name "My First Key"
heidi model serve
```

🎉 **That's it! Heidi CLI is now installed and ready to use!**

> **💡 Tip**: If you get "command not found" after installation, see [**QUICK_INSTALL.md**](QUICK_INSTALL.md) for troubleshooting steps.

---

## 📚 **Complete Documentation**

**📖 Step-by-Step Guide**: [**docs/how-to-use.md**](docs/how-to-use.md)

From your first model download to enterprise deployment, our comprehensive guide covers:
- ✅ **Quick Start** - Get running in 5 minutes
- ✅ **Setup & Configuration** - Configure your environment  
- ✅ **Model Management** - Download and manage models
- ✅ **HuggingFace Integration** - Access 100,000+ models
- ✅ **Token & Cost Tracking** - Monitor usage and costs
- ✅ **Analytics & Monitoring** - Performance insights
- ✅ **Advanced Features** - Power user capabilities
- ✅ **Enterprise Deployment** - Production setup
- ✅ **Troubleshooting** - Common issues and solutions

---

## 🚀 **How the Magic Actually Happens (The 5-Phase Loop)**

Think of Heidi like a "Perception-Action-Learning" loop. She's got five internal modules that play together like a well-oiled (and slightly sarcastic) machine:

#### 1. The Multi-Model Host (`src/model_host`)
Stop talking to the cloud! Heidi hosts your models right here on your machine (without Ollama and local transformers). 
*   **What it does:** Gives you a unified, OpenAI-compatible API (`/v1/chat/completions`).
*   **The "Secret Sauce":** You can route requests to different models—like a "stable" one for real work and an "experimental" one for when you're feeling spicy—without ever touching your app code.

#### 2. Runtime Learning & Memory (`src/runtime`)
Heidi doesn't like starting from zero every time.
*   **What it does:** Uses a SQLite database for both short-term "what just happened?" and long-term "wait, I remember this!" memory.
*   **The "Secret Sauce":** Once a task is done, the **Reflection Engine** kicks in. It scores how well it did (Reward Scoring) and saves "pro-tips" that worked. Next time you ask something similar, Heidi whispers those successful strategies back into the prompt. It's basically cheating, but legal.

#### 3. The Data Pipeline (`src/pipeline`)
Clean data = happy AI. 
*   **What it does:** Grabs every single interaction and stuffs them into dated "Run Folders."
*   **The "Secret Sauce":** A **Curation Engine** digests these runs, tosses out the garbage, and applies a **Secret Redaction Layer**. It scrubs your OpenAI keys, deep-rooted secrets, and embarrassing passwords before they ever touch the retraining loop. Privacy is cool, okay?

#### 4. Registry & Atomic Hot-Swap (`src/registry`)
When you've got enough data, it's time to level up.
*   **What it does:** Manages a **Model Registry** with stable and candidate channels (think of it like "Production" vs. "Beta"). 
*   **The "Secret Sauce":** After retraining, an **Eval Harness** checks if the new model is actually better or if it's just hallucinating harder. If it passes, Heidi does an **Atomic Hot-Swap**—reloading the new model in milliseconds with zero downtime.

#### 5. HuggingFace Integration (`src/integrations`) 
Discover, download, and manage models from the world's largest AI model hub.
*   **What it does:** Seamlessly integrates with HuggingFace Hub for model discovery and management.
*   **The "Secret Sauce":** Smart auto-configuration based on model metadata, usage analytics, and intelligent recommendations. Turns generic models into specialized tools with zero manual configuration.

---

### Commands You'll Actually Use

| Feature | The Command | What's it for? |
| :--- | :--- | :--- |
| **Model Hosting** | `heidi model serve` | Spins up local server. Easy peasy. |
| **Agent Memory** | `heidi memory search` | Digging through the agent's brain for that one thing. |
| **Reflection** | `heidi learning reflect` | Forces the agent to think about what it just did. |
| **Data Export** | `heidi learning export` | Bags up curated/redacted data for retraining. |
| **Promotion** | `heidi learning promote` | Moves a "Candidate" model to "Stable" status. |
| **System Health** | `heidi doctor` | Makes sure everything isn't on fire. |
| **HuggingFace Hub** | `heidi hf search <query>` | Search models on HuggingFace Hub |
| **HuggingFace Hub** | `heidi hf info <model>` | Get detailed model information |
| **HuggingFace Hub** | `heidi hf download <model>` | Download model and auto-configure |
| **HuggingFace Hub** | `heidi hf list-local` | List downloaded models |
| **HuggingFace Hub** | `heidi hf compare <model1> <model2>` | Compare models with recommendations |
| **HuggingFace Hub** | `heidi hf batch-download <model1> <model2>` | Download multiple models in parallel |
| **HuggingFace Hub** | `heidi hf analytics [model]` | View usage analytics and performance |
| **HuggingFace Hub** | `heidi hf remove <model>` | Remove downloaded model |

---

### Why does the AI Community even care?

Let's be real, the current AI world is a bit of a mess. Heidi fixes the big headaches:

1.  **Privacy is King:** Most learning happens in the cloud. Nope. Heidi keeps your training data, your memory, and your weights 100% on your machine. Your company secrets stay *your* secrets.
2.  **Stopping the "Stupid Loop":** We've all seen agents make the same mistake twice. Heidi's **Redaction & Reflection** layers make sure the model actually gets *better* at your specific job, not just weirder.
3.  **MLOps for the rest of us:** Usually, you need a team of engineers to build retraining pipelines. Heidi abstracts all that noise into a single CLI tool. Now you can run a professional-grade Model Lab from your bedroom.
4.  **Access to Thousands of Models:** Why limit yourself to a few models? Heidi's HuggingFace integration gives you access to thousands of models with smart auto-configuration and usage analytics.

---

### How to get this thing running

**1. Install the bits:**
```bash
python -m pip install -e '.[dev]'
```

**2. Check the vitals:**
```bash
# This makes sure your state/ directories and docs are alive
heidi doctor
```

**3. Fire it up:**
```bash
# Start the model host and wait for the "Serving" message
heidi model serve
```

**4. Check your status:**
```bash
heidi status
```

**5. Discover and Download Models:**
```bash
# Search for models on HuggingFace Hub
heidi hf search "mistral" --limit 5

# Get detailed information about a model
heidi hf info "microsoft/DialoGPT-small"

# Download and auto-configure a model
heidi hf download "microsoft/DialoGPT-small" --add-to-config

# Compare multiple models
heidi hf compare "microsoft/DialoGPT-small" "mistralai/Mistral-7B-Instruct-v0.2"

# Batch download multiple models
heidi hf batch-download "model1" "model2" "model3"

# View usage analytics
heidi hf analytics

# List your downloaded models
heidi hf list-local
```

---

### Real-World Examples

**Model Discovery:**
```bash
# Find the perfect model for your needs
heidi hf search "coding" --limit 10

# Compare models side-by-side
heidi hf compare "codellama/CodeLlama-7b-Instruct-hf" "WizardLM/WizardCoder-15B-V1.0"

# Get detailed model information
heidi hf info "meta-llama/Llama-2-7b-chat-hf"
```

**Smart Downloads:**
```bash
# Download with automatic configuration
heidi hf download "microsoft/DialoGPT-small" --add-to-config

# Batch download for efficiency
heidi hf batch-download "microsoft/DialoGPT-small" "meta-llama/Llama-3.2-1B-Instruct"

# Models are stored in ~/.heidi/models/huggingface/
# Automatically configured for immediate use
```

**Usage Analytics:**
```bash
# Track model performance and usage patterns
heidi hf analytics

# Get detailed analytics for a specific model
heidi hf analytics "microsoft_DialoGPT-small" --days 7

# Export analytics data for analysis
heidi hf analytics --export
```

**Production Deployment:**
```bash
# Start serving multiple models
heidi model serve

# Models appear in OpenAI-compatible API
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "microsoft_DialoGPT-small", "messages": [{"role": "user", "content": "Hello!"}]}'

# Rich metadata in model listings
curl http://127.0.0.1:8000/v1/models | jq '.data[] | {id, display_name, capabilities, huggingface}'
```

---

### Architecture Overview

```
heidi-cli/
├── src/heidi_cli/
│   ├── model_host/          # Multi-model API server
│   │   ├── server.py      # FastAPI server with OpenAI endpoints
│   │   ├── manager.py     # Model routing and request handling
│   │   └── metadata.py    # Rich model metadata management
│   ├── runtime/             # Learning & memory system
│   │   ├── db.py          # SQLite database management
│   │   ├── reflection.py   # Performance analysis
│   │   └── curation.py    # Data cleaning and redaction
│   ├── pipeline/            # Data export pipeline
│   │   └── curation.py    # Smart data curation
│   ├── registry/            # Model versioning and hot-swap
│   │   ├── manager.py     # Model registry management
│   │   ├── eval.py        # Model evaluation
│   │   └── hotswap.py     # Zero-downtime model swapping
│   ├── integrations/        # External integrations
│   │   ├── huggingface.py # HuggingFace Hub integration
│   │   └── analytics.py   # Usage analytics system
│   └── cli.py             # Unified command interface
└── state/                  # Local data storage
    ├── models/              # Downloaded models
    ├── registry/            # Model versions
    ├── memory/              # Agent memory
    ├── logs/                # System logs
    └── analytics/           # Usage analytics database
```

---

### Key Features

**Model Discovery:**
- Search thousands of models on HuggingFace Hub
- Filter by task, size, capabilities, and popularity
- Get detailed model information and metadata
- Compare models side-by-side with intelligent recommendations

**Smart Configuration:**
- Automatic model configuration based on metadata
- Capability detection (chat, coding, vision, embeddings)
- Device requirements based on model size
- Context length and token optimization

**Usage Analytics:**
- Real-time request tracking and performance metrics
- Latency analysis (P95, P99, throughput)
- Error monitoring and success rates
- Token efficiency calculations
- Export functionality for external analysis

**Batch Operations:**
- Parallel model downloads (up to 3 concurrent)
- Progress tracking and error handling
- Automatic configuration for multiple models
- Comprehensive summary reports

**API Integration:**
- OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`)
- Rich metadata in model listings
- Seamless integration with existing tools
- Automatic capability detection and routing

---

### Use Cases

**Developers:**
- Test different models for specific tasks
- Compare performance across model families
- Batch download model collections
- Track usage patterns and optimize costs

**Enterprises:**
- Manage model fleets with analytics
- Enforce model governance and compliance
- Optimize resource allocation
- Track ROI on model investments

**Researchers:**
- Access thousands of models for experimentation
- Compare model architectures and capabilities
- Track performance metrics across models
- Export data for academic analysis

---

### Advanced Configuration

**Model Storage:**
```bash
# Models are stored in ~/.heidi/models/huggingface/
# Each model has its own directory with metadata
# HuggingFace cache structure for efficient storage
```

**Analytics Database:**
```bash
# SQLite database at ~/.heidi/analytics/usage.db
# Tracks requests, performance, errors, and trends
# Thread-safe for concurrent access
# Exportable for external analysis
```

**Configuration:**
```bash
# Heidi config at ~/.heidi/config/suite.json
# Automatic model configuration
# Capability detection and optimization
# Device and precision settings
```

---

### Why Heidi CLI?

1. **Privacy First:** Your data, your models, your rules. Everything stays local.
2. **Smart Automation:** From model discovery to performance tracking, it just works.
3. **Professional Grade:** Enterprise-ready features with monitoring and analytics.
4. **Cost Effective:** No cloud fees, no subscription traps.
5. **Open Source:** Full transparency and extensibility.
6. **HuggingFace Powered:** Access to thousands of models with one command.
7. **Complete Documentation:** Step-by-step guide for all users.

---

*Heidi is written by humans (mostly) to help machines act more like humans (the smart ones).*

---

## 📚 Complete Documentation

**📖 Step-by-Step Guide**: [**docs/how-to-use.md**](docs/how-to-use.md)

From your first model download to enterprise deployment, our comprehensive guide covers:
- ✅ **Quick Start** - Get running in 5 minutes
- ✅ **Setup & Configuration** - Configure your environment  
- ✅ **Model Management** - Download and manage models
- ✅ **HuggingFace Integration** - Access 100,000+ models
- ✅ **Token & Cost Tracking** - Monitor usage and costs
- ✅ **Analytics & Monitoring** - Performance insights
- ✅ **Advanced Features** - Power user capabilities
- ✅ **Enterprise Deployment** - Production setup
- ✅ **Troubleshooting** - Common issues and solutions

---

## Quick Start

```bash
# 1. Install
pip install heidi-cli

# 2. Setup
heidi setup

# 3. Discover Models
heidi hf search "text-generation" --limit 5

# 4. Download Your Favorite
heidi hf download "microsoft/DialoGPT-small" --add-to-config

# 5. Start Serving
heidi model serve

# 6. Use It!
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "microsoft_DialoGPT-small", "messages": [{"role": "user", "content": "Hello!"}]}'
```

**That's it! You're now running a professional-grade AI model hosting platform with HuggingFace integration.** 
