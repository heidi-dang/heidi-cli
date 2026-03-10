# 🔌 Platform Integration Guide

## **🎯 Overview**

Heidi CLI provides a **pure model hosting platform** with OpenAI-compatible API endpoints. Any autonomous coding platform can connect to Heidi and use its models for their agent work.

---

## **🚀 Quick Integration (5 Minutes)**

### **Step 1: Start Heidi CLI**
```bash
# Install Heidi CLI
pip install --break-system-packages -e .

# Start model host
heidi model serve
```

### **Step 2: Configure Your Platform**
```bash
# Point your platform to Heidi's API
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="heidi-hosted-models"  # Any value works
```

### **Step 3: Use Models**
```python
import openai

client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="heidi-hosted-models"
)

# List available models
models = client.models.list()
for model in models.data:
    print(f"Available: {model.id}")

# Use a model
response = client.chat.completions.create(
    model="opencode-gpt-4",
    messages=[{"role": "user", "content": "Write Python code"}]
)
```

---

## **📋 Available Models**

### **OpenCode Models (Cloud)**
```json
{
  "id": "opencode-gpt-4",
  "display_name": "GPT-4 (OpenCode)",
  "capabilities": ["chat", "coding", "function_calling", "streaming"],
  "context_length": 128000,
  "pricing": {"input_tokens": 0.03, "output_tokens": 0.06}
}
```

**Available Models:**
- `opencode-gpt-4` - General purpose, large model
- `opencode-gpt-4-turbo` - Fast, recent knowledge
- `opencode-claude-3-opus` - Complex reasoning, safe
- `opencode-claude-3-sonnet` - Balanced performance
- `opencode-claude-3-haiku` - Fast, efficient

### **Local Models (Self-Hosted)**
```json
{
  "id": "v-96ad402f",
  "display_name": "v-96ad402f",
  "capabilities": ["chat", "coding", "streaming"],
  "context_length": 4096,
  "provider": "local"
}
```

---

## **🔧 Platform-Specific Integration**

### **1. OpenCode Integration**
```bash
# OpenCode configuration
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="heidi-cli"

# Use with OpenCode CLI
opencode --model opencode-gpt-4 --task "build-react-app"
```

### **2. Cursor.dev Integration**
```json
// Cursor settings.json
{
  "models": {
    "provider": "openai-compatible",
    "baseUrl": "http://127.0.0.1:8000/v1",
    "apiKey": "heidi-cli",
    "models": ["opencode-gpt-4", "opencode-claude-3-sonnet"]
  }
}
```

### **3. Continue.dev Integration**
```bash
# Continue configuration
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="heidi-cli"

# Use Continue
continue --model opencode-gpt-4
```

### **4. Aider Integration**
```bash
# Aider configuration
export OPENAI_API_KEY="heidi-cli"
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"

# Use Aider
aider --model opencode-gpt-4
```

### **5. Custom Agent Integration**
```python
# Any custom agent can connect
class MyCodingAgent:
    def __init__(self):
        self.llm = openai.OpenAI(
            base_url="http://127.0.0.1:8000/v1",
            api_key="heidi-cli"
        )
    
    async def build_app(self, spec: str):
        # Use Heidi's models for reasoning
        plan = await self.llm.chat.completions.create(
            model="opencode-gpt-4",
            messages=[{"role": "user", "content": f"Plan: {spec}"}]
        )
        
        # Execute plan (agent logic lives here)
        return await self.execute_plan(plan)
```

---

## **🌐 API Endpoints**

### **OpenAI-Compatible Endpoints**
```bash
# List models
GET /v1/models

# Get specific model
GET /v1/models/{model_id}

# Chat completion
POST /v1/chat/completions

# Health check
GET /health
```

### **Enhanced Model Metadata**
```bash
curl http://127.0.0.1:8000/v1/models/opencode-gpt-4
```

**Response:**
```json
{
  "id": "opencode-gpt-4",
  "display_name": "GPT-4 (OpenCode)",
  "description": "OpenCode's GPT-4 model for general purpose tasks",
  "capabilities": ["chat", "coding", "function_calling", "streaming"],
  "context_length": 128000,
  "max_output_tokens": 4096,
  "status": "available",
  "provider": "opencode",
  "tags": ["general", "coding", "large"],
  "version": "1.0",
  "pricing": {
    "input_tokens": 0.03,
    "output_tokens": 0.06,
    "currency": "USD",
    "unit": "per_1k_tokens"
  }
}
```

---

## **📊 Monitoring and Health**

### **Health Check**
```bash
curl http://127.0.0.1:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.1",
  "uptime_seconds": 1234.56,
  "models": {
    "total": 6,
    "available": 6,
    "loading": 0,
    "error": 0
  },
  "requests": {
    "total": 42,
    "avg_latency_ms": 245.3,
    "error_rate": 0.02
  },
  "services": {
    "opencode_api": true,
    "local_models": true,
    "registry": true
  }
}
```

### **Model Metrics**
```bash
# Check model-specific metrics
curl http://127.0.0.1:8000/v1/models/opencode-gpt-4
```

**Response includes:**
- `avg_latency_ms` - Average response time
- `requests_per_minute` - Current request rate
- `success_rate` - Success percentage
- `last_updated` - When metrics were last updated

---

## **🔧 Advanced Configuration**

### **Model Selection Strategy**
```python
# Smart model selection based on task
def select_model(task_type: str, complexity: str):
    if task_type == "coding":
        if complexity == "simple":
            return "opencode-claude-3-haiku"  # Fast, cheap
        elif complexity == "complex":
            return "opencode-gpt-4"  # Capable
        else:
            return "opencode-claude-3-sonnet"  # Balanced
    elif task_type == "reasoning":
        return "opencode-claude-3-opus"  # Best reasoning
    else:
        return "opencode-gpt-4-turbo"  # General purpose
```

### **Load Balancing**
```python
# Simple round-robin load balancing
models = ["opencode-gpt-4", "opencode-claude-3-sonnet"]
current_index = 0

def get_next_model():
    global current_index
    model = models[current_index]
    current_index = (current_index + 1) % len(models)
    return model
```

### **Error Handling**
```python
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def chat_with_retry(model, messages):
    try:
        return client.chat.completions.create(
            model=model,
            messages=messages
        )
    except openai.APIError as e:
        logger.error(f"API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## **🎯 Best Practices**

### **1. Model Selection**
- **Simple tasks**: Use `opencode-claude-3-haiku` (fast, cheap)
- **Complex coding**: Use `opencode-gpt-4` (most capable)
- **Reasoning**: Use `opencode-claude-3-opus` (best reasoning)
- **Balanced**: Use `opencode-claude-3-sonnet` (speed + capability)

### **2. Error Handling**
- Implement retry logic with exponential backoff
- Check model availability before requests
- Handle rate limits gracefully
- Log errors for debugging

### **3. Performance**
- Use streaming for long responses
- Cache identical requests when possible
- Monitor latency and error rates
- Choose models based on task complexity

### **4. Security**
- Validate API responses
- Sanitize user inputs
- Monitor for abuse
- Use appropriate model permissions

---

## **🧪 Testing Integration**

### **Basic Connectivity Test**
```python
import openai

def test_heidi_connection():
    try:
        client = openai.OpenAI(
            base_url="http://127.0.0.1:8000/v1",
            api_key="test-key"
        )
        
        # Test health
        response = client.chat.completions.create(
            model="opencode-gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        print("✅ Connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
```

### **Model Capabilities Test**
```python
def test_model_capabilities():
    client = openai.OpenAI(
        base_url="http://127.0.0.1:8000/v1",
        api_key="test-key"
    )
    
    # Test coding capability
    response = client.chat.completions.create(
        model="opencode-gpt-4",
        messages=[{
            "role": "user", 
            "content": "Write a Python function to calculate fibonacci numbers"
        }]
    )
    
    # Verify response contains Python code
    assert "def" in response.choices[0].message.content
    print("✅ Coding capability verified!")
```

---

## **📞 Support and Troubleshooting**

### **Common Issues**

#### **1. Connection Refused**
```bash
# Make sure Heidi is running
heidi status
heidi model serve
```

#### **2. Model Not Available**
```bash
# Check available models
curl http://127.0.0.1:8000/v1/models

# Check model status
curl http://127.0.0.1:8000/health
```

#### **3. High Latency**
```bash
# Check metrics
curl http://127.0.0.1:8000/health

# Consider using faster models
# opencode-claude-3-haiku for simple tasks
# opencode-gpt-4-turbo for general use
```

#### **4. API Key Issues**
```bash
# Heidi doesn't validate API keys
# Use any value for OPENAI_API_KEY
export OPENAI_API_KEY="heidi-hosted-models"
```

### **Getting Help**
- Check Heidi CLI status: `heidi status`
- Review health endpoint: `curl http://127.0.0.1:8000/health`
- Check logs: `heidi doctor`
- Review integration examples above

---

## **🎉 Success Stories**

### **OpenCode Platform**
```bash
# Before: Direct OpenAI API
export OPENAI_API_KEY="sk-..."
# Cost: $0.06 per 1K tokens

# After: Heidi CLI hosting
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="heidi-cli"
# Benefits: Model management, cost control, local models
```

### **Custom AI Agent**
```python
# Agent can now choose optimal models
def select_model_for_task(task):
    if task.is_simple():
        return "opencode-claude-3-haiku"  # $0.00125 per 1K tokens
    elif task.needs_reasoning:
        return "opencode-claude-3-opus"  # $0.075 per 1K tokens
    else:
        return "opencode-gpt-4"  # $0.06 per 1K tokens
```

---

## **🚀 Next Steps**

1. **Start Heidi CLI**: `heidi model serve`
2. **Configure your platform**: Set `OPENAI_BASE_URL`
3. **Test integration**: Use basic connectivity test
4. **Optimize model selection**: Choose models based on tasks
5. **Monitor performance**: Use health endpoint
6. **Scale up**: Add more models as needed

**Your autonomous coding platform is now powered by Heidi CLI!** 🌟

---

## **📚 Additional Resources**

- [Heidi CLI Documentation](./README.md)
- [Model Hosting Roadmap](./MODEL_HOSTING_ROADMAP.md)
- [API Reference](./API_REFERENCE.md)
- [Examples and Samples](../examples/)

**For support, check the health endpoint and logs, or run `heidi doctor` for diagnostics.**
