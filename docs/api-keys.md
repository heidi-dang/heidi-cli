# 🔑 Heidi API Keys - Unified Model Access

> **One API Key to Rule Them All**  
> Use a single Heidi API key to access models from any provider - local, HuggingFace, OpenCode, and more!

---

## 📋 **Table of Contents**

1. [🚀 Quick Start](#-quick-start) - Generate and use your first API key
2. [🔑 API Key Management](#-api-key-management) - Generate, list, and manage keys
3. [🌐 API Usage](#-api-usage) - Use API keys in your applications
4. [🤖 Model Access](#-model-access) - Access different model providers
5. [📊 Rate Limiting](#-rate-limiting) - Understanding usage limits
6. [🔒 Security](#-security) - Best practices for API key security
7. [💼 Integration Examples](#-integration-examples) - Real-world usage examples

---

## 🚀 **Quick Start**

### **Step 1: Generate Your API Key**
```bash
# Generate a new API key
heidi api generate --name "My App Key" --user "my-user-id"

# Example output
🔑 API Key: heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo
```

### **Step 2: Use It in Your Application**
```python
import requests

# Set up your request
headers = {
    "Authorization": "Bearer heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo",
    "Content-Type": "application/json"
}

data = {
    "model": "local://my-model",
    "messages": [{"role": "user", "content": "Hello!"}]
}

# Make the request
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers=headers,
    json=data
)

print(response.json())
```

### **Step 3: Start Building!**
That's it! You now have a unified API key that works across all Heidi-managed models.

---

## 🔑 **API Key Management**

### **Generate API Keys**
```bash
# Basic key generation
heidi api generate --name "Production Key" --user "user123"

# Advanced options
heidi api generate \
  --name "Production Key" \
  --user "user123" \
  --expires 30 \
  --rate-limit 200 \
  --permissions "read,write,admin"
```

**Options:**
- `--name`: Descriptive name for the key
- `--user`: User ID (default: "default")
- `--expires`: Days until expiration (optional)
- `--rate-limit`: Requests per minute (default: 100)
- `--permissions`: Comma-separated permissions (default: "read,write")

### **List API Keys**
```bash
# List all keys for a user
heidi api list --user "user123"

# Example output
┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Key ID      ┃ Name     ┃ Created    ┃ Expires ┃ Status    ┃ Usage      ┃ Rate Limit ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 5e83c033... │ Prod Key │ 2024-03-10 │ 2024-04-10 │ ✅ Active │ 1,234 req │ 200/min    │
└─────────────┴──────────┴────────────┴─────────┴───────────┴────────────┴────────────┘
```

### **Revoke API Keys**
```bash
# Revoke a specific key
heidi api revoke "5e83c033-16d1-4eb6-8ad4-f103d5018a64"
```

### **View Usage Statistics**
```bash
# Get detailed usage stats
heidi api stats "5e83c033-16d1-4eb6-8ad4-f103d5018a64"

# Example output
📊 Usage Statistics for 5e83c033...
┌─────────────────┬─────────────────┐
│ Total Requests  │ 1,234           │
│ Created         │ 2024-03-10      │
│ Last Used       │ 2024-03-10 15:30│
│ Days Active     │ 10              │
│ Avg Daily Usage │ 123.4 requests  │
└─────────────────┴─────────────────┘
```

---

## 🌐 **API Usage**

### **Authentication**
Heidi API uses Bearer token authentication:

```bash
# Environment variable
export HEIDI_API_KEY=heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo

# HTTP Header
Authorization: Bearer heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo
```

### **API Endpoints**

#### **Chat Completions**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local://my-model",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

#### **List Models**
```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### **Rate Limit Info**
```bash
curl -X GET http://localhost:8000/v1/rate-limit \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### **User Info**
```bash
curl -X GET http://localhost:8000/v1/user/info \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 🤖 **Model Access**

Heidi API provides unified access to multiple model providers:

### **Model Identifier Format**
```
provider://model-id
```

**Available Providers:**
- `local://` - Local models hosted by Heidi
- `hf://` - HuggingFace models
- `opencode://` - OpenCode models
- `heidi://` - Heidi-specific models (defaults to local)

### **Examples**
```json
{
  "model": "local://my-gpt-model",
  "model": "hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0",
  "model": "opencode://gpt-4",
  "model": "heidi://specialized-model"
}
```

### **List Available Models**
```bash
heidi api models

# Example output
🤖 Local Models:
  • local://opencode-gpt-4 - OpenCode's GPT-4 model
  • local://my-custom-model - Custom trained model

🤖 HuggingFace Models:
  • hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0 - Small conversational model
  • hf://microsoft/DialoGPT-small - Conversational AI model

📖 Usage Examples:
• Local model: local://my-model
• HuggingFace: hf://model-name
• OpenCode: opencode://gpt-4
```

---

## 📊 **Rate Limiting**

### **How Rate Limiting Works**
- **Per-key rate limiting** - Each API key has its own limits
- **Sliding window** - Requests counted over last 60 seconds
- **Automatic reset** - Limits reset automatically every minute

### **Rate Limit Headers**
When you make API requests, you'll get rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1647123456
```

### **Handling Rate Limits**
```python
import requests
import time

def make_api_request_with_retry(api_key, data):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    while True:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 429:
            # Rate limited - wait and retry
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        
        response.raise_for_status()
        return response.json()
```

---

## 🔒 **Security Best Practices**

### **API Key Security**
- ✅ **Store securely** - Use environment variables or secret management
- ✅ **Rotate regularly** - Generate new keys periodically
- ✅ **Limit permissions** - Only grant necessary permissions
- ✅ **Monitor usage** - Check usage stats regularly
- ❌ **Don't commit to code** - Never hardcode API keys
- ❌ **Don't share publicly** - Keep keys private

### **Environment Variables**
```bash
# Set in your environment
export HEIDI_API_KEY=heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo

# Use in application
import os
api_key = os.getenv("HEIDI_API_KEY")
```

### **Secret Management**
```python
# Using python-dotenv
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("HEIDI_API_KEY")
```

### **Key Rotation Strategy**
1. **Generate new key**: `heidi api generate --name "New Key" --user "user123"`
2. **Update application**: Replace old key with new one
3. **Test thoroughly**: Ensure new key works
4. **Revoke old key**: `heidi api revoke "old-key-id"`

---

## 💼 **Integration Examples**

### **Python Integration**
```python
import requests
import os

class HeidiClient:
    def __init__(self, api_key=None, base_url="http://localhost:8000"):
        self.api_key = api_key or os.getenv("HEIDI_API_KEY")
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat(self, model, messages, **kwargs):
        data = {"model": model, "messages": messages, **kwargs}
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
client = HeidiClient()
response = client.chat(
    model="local://my-model",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### **JavaScript Integration**
```javascript
class HeidiClient {
    constructor(apiKey, baseUrl = 'http://localhost:8000') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async chat(model, messages, options = {}) {
        const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                model: model,
                messages: messages,
                ...options
            })
        });
        
        return response.json();
    }
}

// Usage
const client = new HeidiClient('your-api-key');
client.chat('local://my-model', [
    {role: 'user', content: 'Hello!'}
]).then(response => console.log(response));
```

### **cURL Integration**
```bash
#!/bin/bash

API_KEY="heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo"
BASE_URL="http://localhost:8000"

# Chat completion
curl -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local://my-model",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# List models
curl -X GET "${BASE_URL}/v1/models" \
  -H "Authorization: Bearer ${API_KEY}"
```

### **Docker Integration**
```dockerfile
FROM python:3.9

# Set API key as environment variable
ENV HEIDI_API_KEY=heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY app.py .

# Run the application
CMD ["python", "app.py"]
```

---

## 🎯 **Use Cases**

### **Web Applications**
- **Chat interfaces** - Add AI chat to your web app
- **Content generation** - Generate articles, summaries, etc.
- **Code assistance** - Help with coding tasks

### **Mobile Apps**
- **AI assistants** - Voice/text AI assistants
- **Translation** - Multi-language support
- **Content moderation** - Automated content filtering

### **Enterprise Integration**
- **Internal tools** - AI-powered internal applications
- **Customer support** - Automated support responses
- **Data analysis** - AI-powered data insights

### **Developer Tools**
- **IDE plugins** - AI assistance in code editors
- **CLI tools** - Command-line AI helpers
- **API services** - AI-powered microservices

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Invalid API Key**
```
Error: 401 Unauthorized - Invalid API key
```
**Solution**: Check your API key and ensure it's active.

#### **Rate Limited**
```
Error: 429 Too Many Requests - Rate limit exceeded
```
**Solution**: Wait and retry, or request higher rate limits.

#### **Model Not Found**
```
Error: 404 Not Found - Model not available
```
**Solution**: Check available models with `heidi api models`.

#### **Connection Error**
```
Error: Connection refused
```
**Solution**: Ensure Heidi API server is running with `heidi api server`.

### **Getting Help**
```bash
# Check API configuration
heidi api config

# List available models
heidi api models

# Check API key status
heidi api list --user "your-user-id"

# Get help
heidi api --help
```

---

## 📚 **Additional Resources**

### **Documentation**
- **API Reference**: `docs/api-reference.md`
- **Model Management**: `docs/model-management.md`
- **Troubleshooting**: `docs/troubleshooting.md`

### **Examples**
- **Python Client**: `examples/api_demo.py`
- **Web Integration**: `examples/web_integration/`
- **Mobile Integration**: `examples/mobile_integration/`

### **Community**
- **GitHub Issues**: `https://github.com/heidi-dang/heidi-cli/issues`
- **Discord**: `https://discord.gg/heidi-cli`
- **Documentation**: `https://docs.heidi-cli.com`

---

## 🎉 **Congratulations!**

You now have a **Heidi API key** that provides unified access to all AI models!

**What you can do:**
- ✅ **Access any model** with a single API key
- ✅ **Switch providers** without changing your code
- ✅ **Monitor usage** with built-in analytics
- ✅ **Control access** with rate limiting and permissions
- ✅ **Scale easily** with enterprise-grade features

**Ready to build?** Check out the examples and start integrating!

---

*Last updated: March 2026*  
*API version: 1.0.0*  
*Heidi CLI version: 0.1.1*
