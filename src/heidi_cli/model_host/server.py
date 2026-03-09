from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
    try:
        models = manager.list_models()
        return {"object": "list", "data": models}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible completions endpoint."""
    try:
        response = await manager.get_response(
            model_id=request.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens
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
