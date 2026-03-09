from __future__ import annotations

import logging
from typing import Dict, Any, List
from ..shared.config import ConfigLoader, ModelConfig

logger = logging.getLogger("heidi.model_host")

class ModelManager:
    """Manages local model loading and routing."""
    
    def __init__(self):
        self.config = ConfigLoader.load()
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, ModelConfig] = {m.id: m for m in self.config.models}

    def list_models(self) -> List[Dict[str, Any]]:
        """List routable models for /v1/models."""
        models = []
        for mid, cfg in self.model_configs.items():
            models.append({
                "id": mid,
                "object": "model",
                "created": 1677610602,
                "owned_by": "heidi-local",
                "permission": [],
                "root": str(cfg.path),
                "parent": None,
            })
        return models

    async def get_response(self, model_id: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Route request to the correct model and get response."""
        if model_id not in self.model_configs:
            raise ValueError(f"Model {model_id} not found in configuration.")
        
        cfg = self.model_configs[model_id]
        if not cfg.path.exists():
            raise FileNotFoundError(f"Model path for {model_id} does not exist: {cfg.path}")
            
        # Placeholder for real model execution
        # In a real implementation, this would call transformers/vLLM/etc.
        logger.info(f"Serving request with model: {model_id}")
        
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

# Global manager instance
manager = ModelManager()
