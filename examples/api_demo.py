#!/usr/bin/env python3
"""
Heidi API Demo

Demonstrates how to use Heidi API keys to access models from any application.
"""

import requests
import json
import time


class HeidiAPIClient:
    """Simple client for Heidi API."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(self, model: str, messages: list, temperature: float = 1.0, max_tokens: int = None):
        """Create a chat completion."""
        url = f"{self.base_url}/v1/chat/completions"
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def list_models(self):
        """List available models."""
        url = f"{self.base_url}/v1/models"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_rate_limit(self):
        """Get rate limit information."""
        url = f"{self.base_url}/v1/rate-limit"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_user_info(self):
        """Get user information."""
        url = f"{self.base_url}/v1/user/info"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


def main():
    """Demo the Heidi API."""
    
    # Replace with your actual API key
    API_KEY = "heidik_OjawUC19Lc6a4YfY5WMJTyR4J1nwQNrcSP0fN6MESbo"
    
    print("🚀 Heidi API Demo")
    print("=" * 50)
    
    # Initialize client
    client = HeidiAPIClient(API_KEY)
    
    try:
        # Get user info
        print("\n📋 User Information:")
        user_info = client.get_user_info()
        print(f"User ID: {user_info['user_id']}")
        print(f"Key Name: {user_info['key_name']}")
        print(f"Rate Limit: {user_info['rate_limit']} requests/minute")
        print(f"Usage Count: {user_info['usage_count']}")
        
        # Get rate limit info
        print("\n📊 Rate Limit:")
        rate_limit = client.get_rate_limit()
        print(f"Limit: {rate_limit['limit']} requests/minute")
        print(f"Used: {rate_limit['used']} requests")
        print(f"Remaining: {rate_limit['remaining']} requests")
        
        # List models
        print("\n🤖 Available Models:")
        models = client.list_models()
        for model in models['data'][:5]:  # Show first 5 models
            print(f"• {model['id']} - {model.get('name', 'Unknown')}")
        
        # Test chat completion
        print("\n💬 Chat Completion Demo:")
        
        # Try different models
        test_models = [
            "local://opencode-gpt-4",
            "hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        ]
        
        for model in test_models:
            print(f"\nTesting {model}:")
            
            messages = [
                {"role": "user", "content": "Hello! Can you tell me a fun fact about space?"}
            ]
            
            try:
                response = client.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=100
                )
                
                content = response['choices'][0]['message']['content']
                usage = response['usage']
                
                print(f"✅ Response: {content[:100]}...")
                print(f"📊 Usage: {usage['total_tokens']} tokens")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n🎉 Demo completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Heidi API server is running")
        print("💡 Start the server with: heidi api server")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
