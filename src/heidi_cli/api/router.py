"""
Heidi API Router

Routes requests to appropriate model providers based on Heidi API key authentication.
Provides a unified interface for all model access.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .key_manager import get_api_key_manager
from .auth import get_authenticator, AuthResult
from ..model_host.manager import ModelManager
from ..integrations.huggingface import get_huggingface_integration
from ..integrations.analytics import UsageAnalytics
from ..token_tracking.models import get_token_database, TokenUsage


class APIRouter:
    """Routes authenticated requests to appropriate model providers."""
    
    def __init__(self):
        self.key_manager = get_api_key_manager()
        self.authenticator = get_authenticator()
        self.model_manager = ModelManager()
        self.huggingface = get_huggingface_integration()
        self.analytics = UsageAnalytics()
        self.token_db = get_token_database()
        self.security = HTTPBearer()
    
    async def route_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Route a request to the appropriate model provider."""
        
        # This will be called after authentication
        # The actual authentication is handled by FastAPI middleware
        
        start_time = time.time()
        
        try:
            # Determine model provider and route
            provider, model_id = self._parse_model_identifier(model)
            
            if provider == "local":
                response = await self._route_to_local_model(
                    model_id, messages, temperature, max_tokens, **kwargs
                )
            elif provider == "huggingface":
                response = await self._route_to_huggingface(
                    model_id, messages, temperature, max_tokens, **kwargs
                )
            elif provider == "opencode":
                response = await self._route_to_opencode(
                    model_id, messages, temperature, max_tokens, **kwargs
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown model provider: {provider}"
                )
            
            # Record usage analytics
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            self._record_usage(
                model, messages, response, response_time_ms, True
            )
            
            return response
            
        except Exception as e:
            # Record failed request
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            self._record_usage(
                model, messages, {}, response_time_ms, False, str(e)
            )
            
            raise HTTPException(
                status_code=500,
                detail=f"Model request failed: {str(e)}"
            )
    
    def _parse_model_identifier(self, model: str) -> tuple[str, str]:
        """Parse model identifier to determine provider and model ID."""
        
        if model.startswith("local://"):
            return "local", model[8:]
        elif model.startswith("hf://"):
            return "huggingface", model[5:]
        elif model.startswith("opencode://"):
            return "opencode", model[10:]
        elif model.startswith("heidi://"):
            # Heidi-specific model - route to local by default
            return "local", model[8:]
        else:
            # Default to local for backward compatibility
            return "local", model
    
    async def _route_to_local_model(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Route request to local model manager."""
        
        try:
            response = await self.model_manager.get_response(
                model_id, messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
            return response
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Local model unavailable: {str(e)}"
            )
    
    async def _route_to_huggingface(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Route request to HuggingFace model."""
        
        try:
            # Convert messages to prompt
            prompt = self._messages_to_prompt(messages)
            
            # Use HuggingFace inference API
            response = await self.huggingface.generate_text(
                model_id, prompt, temperature=temperature, max_tokens=max_tokens
            )
            
            # Format response like OpenAI
            return {
                "id": f"hf-{model_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response.split()),
                    "total_tokens": len(prompt.split()) + len(response.split())
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"HuggingFace model unavailable: {str(e)}"
            )
    
    async def _route_to_opencode(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Route request to OpenCode API."""
        
        try:
            # This would integrate with OpenCode API
            # For now, fallback to local model
            return await self._route_to_local_model(
                model_id, messages, temperature, max_tokens, **kwargs
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"OpenCode model unavailable: {str(e)}"
            )
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single prompt string."""
        prompt_parts = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        
        return "\n".join(prompt_parts)
    
    def _record_usage(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: Dict[str, Any],
        response_time_ms: float,
        success: bool,
        error_message: str = None
    ):
        """Record usage analytics and token tracking."""
        
        try:
            # Record analytics
            self.analytics.record_request(
                model_id=model,
                request_tokens=self._estimate_tokens(messages),
                response_tokens=self._extract_response_tokens(response),
                response_time_ms=response_time_ms,
                success=success
            )
            
            # Record token usage
            if success and "usage" in response:
                usage_data = response["usage"]
                token_usage = TokenUsage(
                    model_id=model,
                    session_id="heidi-api",
                    user_id="api-user",  # Will be set by auth middleware
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                    cost_usd=0.0  # Will be calculated based on model pricing
                )
                
                self.token_db.record_usage(token_usage)
                
        except Exception:
            # Don't fail the request if usage tracking fails
            pass
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages."""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        # Rough estimation: 1 token ≈ 4 characters
        return total_chars // 4
    
    def _extract_response_tokens(self, response: Dict[str, Any]) -> int:
        """Extract token count from response."""
        if "usage" in response:
            return response["usage"].get("completion_tokens", 0)
        return 0
    
    def list_available_models(self) -> Dict[str, List[Dict]]:
        """List all available models from all providers."""
        
        models = {
            "local": [],
            "huggingface": [],
            "opencode": []
        }
        
        # Local models
        try:
            local_models = self.model_manager.list_models()
            models["local"] = [
                {
                    "id": f"local://{model.get('id', model.get('name', 'unknown'))}",
                    "name": model.get('name', 'Unknown'),
                    "description": model.get('description', ''),
                    "provider": "local"
                }
                for model in local_models
            ]
        except Exception:
            pass
        
        # HuggingFace models (popular ones)
        try:
            hf_models = [
                {
                    "id": "hf://TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                    "name": "TinyLlama Chat",
                    "description": "Small conversational model",
                    "provider": "huggingface"
                },
                {
                    "id": "hf://microsoft/DialoGPT-small",
                    "name": "DialoGPT Small",
                    "description": "Conversational AI model",
                    "provider": "huggingface"
                }
            ]
            models["huggingface"] = hf_models
        except Exception:
            pass
        
        return models


# Global instance
_api_router = None


def get_api_router() -> APIRouter:
    """Get the global API router instance."""
    global _api_router
    if _api_router is None:
        _api_router = APIRouter()
    return _api_router
