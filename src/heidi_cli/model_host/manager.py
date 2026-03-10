from __future__ import annotations

import json
import logging
import os
import httpx
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator
from ..shared.config import ConfigLoader, ModelConfig
from .metadata import metadata_manager, ModelStatus, ModelMetrics

logger = logging.getLogger("heidi.model_host")

# Lazy imports for transformers
torch = None
transformers = None


def _lazy_imports():
    """Lazy load torch and transformers."""
    global torch, transformers
    if transformers is None:
        import torch
        import transformers
        torch = torch
        transformers = transformers


class ModelManager:
    """Manages local model loading, OpenCode API, and routing with metrics."""
    
    def __init__(self):
        self.config = ConfigLoader.load()
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, ModelConfig] = {m.id: m for m in self.config.models}
        
        # Load model from registry
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None
        self.model_path: Optional[Path] = None
        self._load_model_from_registry()
        
        # OpenCode API client
        self.opencode_client: Optional[httpx.AsyncClient] = None
        self._init_opencode_client()
        
        # Metrics tracking
        self.start_time = time.time()
        self.request_count = 0
        self.total_response_time = 0.0
        self.error_count = 0
    
    def _init_opencode_client(self):
        """Initialize OpenCode API client if API key is configured."""
        api_key = os.environ.get("OPENCODE_API_KEY")
        if api_key:
            self.opencode_client = httpx.AsyncClient(
                base_url="https://api.opencode.ai",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0
            )
            logger.info("OpenCode API client initialized")
        else:
            logger.info("OpenCode API key not found, using local models only")
    
    def _load_model_from_registry(self):
        """Load model from active_stable in registry.json."""
        try:
            registry_path = Path("state/registry/registry.json")
            if not registry_path.exists():
                logger.warning("Registry not found, model not loaded")
                return
            
            with open(registry_path) as f:
                registry = json.load(f)
            
            active_version = registry.get("active_stable")
            if not active_version:
                logger.warning("No active_stable version in registry")
                return
            
            versions = registry.get("versions", {})
            version_info = versions.get(active_version)
            if not version_info:
                logger.warning(f"Version {active_version} not found in registry versions")
                return
            
            model_path = Path(version_info.get("path", ""))
            if not model_path.exists():
                logger.warning(f"Model path does not exist: {model_path}")
                return
            
            self.model_path = model_path
            logger.info(f"Loading model from: {model_path}")
            
            # Lazy import transformers
            _lazy_imports()
            
            # Load tokenizer and model
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                str(model_path),
                trust_remote_code=True
            )
            self.model = transformers.AutoModelForCausalLM.from_pretrained(
                str(model_path),
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_memory_usage=True,
                trust_remote_code=True
            )
            
            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token_id
            
            logger.info(f"Model loaded successfully: {active_version}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.tokenizer = None
            self.model = None
            self.model_path = None

    def list_models(self) -> List[Dict[str, Any]]:
        """List routable models for /v1/models with enhanced metadata."""
        models = []
        
        # Get all models from metadata manager
        all_metadata = metadata_manager.list_models()
        
        for metadata in all_metadata:
            model_dict = {
                "id": metadata.id,
                "object": "model",
                "created": int(metadata.created_at.timestamp()),
                "owned_by": metadata.provider.value,
                "permission": [],
                "root": "https://api.opencode.ai" if metadata.provider.value == "opencode" else "local",
                "parent": None,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "capabilities": [cap.value for cap in metadata.capabilities],
                "context_length": metadata.context_length,
                "max_output_tokens": metadata.max_output_tokens,
                "status": metadata.status.value,
                "provider": metadata.provider.value,
                "tags": metadata.tags,
                "version": metadata.version
            }
            
            # Add pricing if available
            if metadata.pricing:
                model_dict["pricing"] = {
                    "input_tokens": metadata.pricing.input_tokens,
                    "output_tokens": metadata.pricing.output_tokens,
                    "currency": metadata.pricing.currency,
                    "unit": metadata.pricing.unit
                }
            
            # Add metrics if available
            if metadata.metrics:
                model_dict["metrics"] = {
                    "avg_latency_ms": metadata.metrics.avg_latency_ms,
                    "requests_per_minute": metadata.metrics.requests_per_minute,
                    "success_rate": metadata.metrics.success_rate,
                    "last_updated": metadata.metrics.last_updated.isoformat() if metadata.metrics.last_updated else None
                }
            
            models.append(model_dict)
        
        return models

    async def get_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Route request to the correct model and get response with metrics."""
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Check if it's an OpenCode model
            if model_id.startswith("opencode-"):
                response = await self._get_opencode_response(model_id, messages, **kwargs)
            
            # Check if local model is loaded
            elif self.model is None or self.tokenizer is None:
                # Fallback to placeholder response
                logger.warning("Model not loaded, using fallback response")
                response = self._fallback_response(model_id, messages)
            
            else:
                # Use local model
                response = await self._get_local_response(model_id, messages, **kwargs)
            
            # Update metrics
            response_time = time.time() - start_time
            self.total_response_time += response_time
            self._update_model_metrics(model_id, response_time, success=True)
            
            return response
            
        except Exception as e:
            # Update error metrics
            self.error_count += 1
            response_time = time.time() - start_time
            self._update_model_metrics(model_id, response_time, success=False)
            
            logger.error(f"Error in get_response for {model_id}: {e}")
            raise
    
    def _fallback_response(self, model_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Fallback response when model is not available."""
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        response_text = f"[Local {model_id} Response to: {prompt[:50]}...]"
        
        return {
            "id": f"chatcmpl-{model_id}",
            "object": "chat.completion",
            "created": 1677610602,
            "model": model_id,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split())
            }
        }


    async def _get_opencode_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Get response from OpenCode API."""
        if not self.opencode_client:
            raise ValueError("OpenCode API client not initialized")
        
        # Extract actual model name (remove opencode- prefix)
        actual_model = model_id.replace("opencode-", "")
        
        try:
            response = await self.opencode_client.post(
                "/v1/chat/completions",
                json={
                    "model": actual_model,
                    "messages": messages,
                    "temperature": kwargs.get('temperature', 0.7),
                    "max_tokens": kwargs.get('max_tokens', 128),
                    "stop": kwargs.get('stop'),
                    "top_p": kwargs.get('top_p', 1.0),
                    "frequency_penalty": kwargs.get('frequency_penalty', 0.0),
                    "presence_penalty": kwargs.get('presence_penalty', 0.0)
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OpenCode API error: {e}")
            raise ValueError(f"OpenCode API request failed: {e}")
    
    async def stream_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from the correct model."""
        if model_id.startswith("opencode-"):
            async for chunk in self._stream_opencode_response(model_id, messages, **kwargs):
                yield chunk
        else:
            async for chunk in self._stream_local_response(model_id, messages, **kwargs):
                yield chunk
    
    async def _stream_opencode_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from OpenCode API."""
        if not self.opencode_client:
            raise ValueError("OpenCode API client not initialized")
        
        actual_model = model_id.replace("opencode-", "")
        
        try:
            async with self.opencode_client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": actual_model,
                    "messages": messages,
                    "stream": True,
                    "temperature": kwargs.get('temperature', 0.7),
                    "max_tokens": kwargs.get('max_tokens', 128),
                    "stop": kwargs.get('stop'),
                    "top_p": kwargs.get('top_p', 1.0),
                    "frequency_penalty": kwargs.get('frequency_penalty', 0.0),
                    "presence_penalty": kwargs.get('presence_penalty', 0.0)
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        yield line[6:]  # Remove "data: " prefix
        except Exception as e:
            logger.error(f"OpenCode streaming error: {e}")
            raise
    
    async def _stream_local_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from local model."""
        if self.model is None or self.tokenizer is None:
            # Fallback streaming response
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            response_text = f"[Local {model_id} Response to: {prompt[:50]}...]"
            
            chunk = {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion.chunk",
                "created": 1677610602,
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": response_text
                    },
                    "finish_reason": None
                }]
            }
            yield json.dumps(chunk)
            
            # Final chunk
            chunk["choices"][0]["finish_reason"] = "stop"
            yield json.dumps(chunk)
            return
        
        # For local models, we'll simulate streaming by generating full response first
        # then yielding it in chunks (real implementation would use model.generate() with streaming)
        full_response = await self.get_response(model_id, messages, **kwargs)
        content = full_response["choices"][0]["message"]["content"]
        
        # Split content into words for streaming effect
        words = content.split()
        for i, word in enumerate(words):
            chunk = {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion.chunk", 
                "created": 1677610602,
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": word + (" " if i < len(words) - 1 else "")
                    },
                    "finish_reason": None
                }]
            }
            yield json.dumps(chunk)
        
        # Final chunk
        chunk["choices"][0]["delta"] = {}
        chunk["choices"][0]["finish_reason"] = "stop"
        yield json.dumps(chunk)

    async def _get_local_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Get response from local model with enhanced parameters."""
        try:
            # Use chat template
            inputs = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                return_tensors="pt"
            )
            
            # Move inputs to same device as model
            device = next(self.model.parameters()).device
            inputs = inputs.to(device)
            
            # Generate response with enhanced parameters
            outputs = self.model.generate(
                inputs,
                max_new_tokens=kwargs.get('max_tokens', 128),
                do_sample=True,
                temperature=kwargs.get('temperature', 0.7),
                pad_token_id=self.tokenizer.eos_token_id,
                stop_strings=kwargs.get('stop', []),
                top_p=kwargs.get('top_p', 1.0),
                frequency_penalty=kwargs.get('frequency_penalty', 0.0),
                presence_penalty=kwargs.get('presence_penalty', 0.0)
            )
            
            # Decode only the new tokens (skip input)
            input_length = inputs.shape[1]
            response_tokens = outputs[0][input_length:]
            response_text = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
            
            return {
                "id": f"chatcmpl-{model_id}",
                "object": "chat.completion",
                "created": 1677610602,
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": input_length,
                    "completion_tokens": len(response_tokens),
                    "total_tokens": input_length + len(response_tokens)
                }
            }
            
        except Exception as e:
            logger.error(f"Error during local model inference: {e}")
            return self._fallback_response(model_id, messages)
    
    def _update_model_metrics(self, model_id: str, response_time: float, success: bool):
        """Update metrics for a specific model"""
        try:
            metadata = metadata_manager.get_metadata(model_id)
            if metadata:
                # Calculate new metrics
                total_requests = self.request_count
                avg_response_time = self.total_response_time / total_requests
                success_rate = (total_requests - self.error_count) / total_requests
                
                # Update metrics
                metrics = ModelMetrics(
                    avg_latency_ms=avg_response_time * 1000,
                    requests_per_minute=total_requests / ((time.time() - self.start_time) / 60),
                    success_rate=success_rate,
                    last_updated=datetime.now()
                )
                
                metadata_manager.update_model_metrics(model_id, metrics)
        except Exception as e:
            logger.error(f"Failed to update metrics for {model_id}: {e}")
    
    @property
    def uptime(self) -> float:
        """Get manager uptime in seconds"""
        return time.time() - self.start_time
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get overall manager metrics"""
        return {
            "total_requests": self.request_count,
            "avg_latency_ms": (self.total_response_time / self.request_count * 1000) if self.request_count > 0 else 0,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "uptime_seconds": self.uptime
        }

# Global manager instance
manager = ModelManager()
