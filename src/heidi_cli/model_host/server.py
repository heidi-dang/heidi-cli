from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional, AsyncGenerator, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .manager import manager
from ..shared.config import ConfigLoader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heidi.model_host")

app = FastAPI(title="Heidi Local Model Host")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0

@app.get("/health")
async def health():
    """Enhanced health check with detailed status."""
    try:
        models = manager.list_models()
        available_models = [m for m in models if m.get("status") == "available"]
        loading_models = [m for m in models if m.get("status") == "loading"]
        error_models = [m for m in models if m.get("status") == "error"]
        
        return {
            "status": "healthy",
            "version": "0.1.1",
            "uptime_seconds": manager.uptime,
            "models": {
                "total": len(models),
                "available": len(available_models),
                "loading": len(loading_models),
                "error": len(error_models)
            },
            "requests": {
                "total": manager.metrics["total_requests"],
                "avg_latency_ms": manager.metrics["avg_latency_ms"],
                "error_rate": manager.metrics["error_rate"]
            },
            "services": {
                "opencode_api": manager.opencode_client is not None,
                "local_models": manager.model is not None,
                "registry": True  # Registry is always available
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint with enhanced metadata."""
    try:
        models = manager.list_models()
        return {"object": "list", "data": models}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Get detailed information about a specific model."""
    try:
        models = manager.list_models()
        model = next((m for m in models if m["id"] == model_id), None)
        
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible completions endpoint."""
    try:
        if request.stream:
            return StreamingResponse(
                stream_chat_completion(request),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            response = await manager.get_response(
                model_id=request.model,
                messages=[m.model_dump() for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty
            )
            return response
    except ValueError as e:
        logger.warning(f"Invalid model requested: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"Model path error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in chat_completions")
        raise HTTPException(status_code=500, detail="Internal server error")

async def stream_chat_completion(request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Stream chat completion response."""
    try:
        async for chunk in manager.stream_response(
            model_id=request.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

@app.on_event("startup")
async def startup_event():
    logger.info("Heidi Model Host booting...")
    config = ConfigLoader.load()
    logger.info(f"Configuration loaded. Serving {len(config.models)} models.")
    for m in config.models:
        logger.info(f" - Model: {m.id} at {m.path}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Heidi Model Host shutting down...")
