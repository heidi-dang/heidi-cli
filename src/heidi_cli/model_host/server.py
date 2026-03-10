from __future__ import annotations

import json
import logging
<<<<<<< HEAD
import uuid
import uuid
from datetime import datetime
from typing import List, Optional, AsyncGenerator, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
=======
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
>>>>>>> origin/main
from .manager import manager
from ..shared.config import ConfigLoader
from ..token_tracking.models import get_token_database
from ..token_tracking.models import get_token_database
from ..token_tracking.models import get_token_database

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
<<<<<<< HEAD
<<<<<<< HEAD
    stop: Optional[List[str]] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0

class ModelUnloadRequest(BaseModel):
    force: bool = False

class TokenUsageRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    model_id: Optional[str] = None
    days: Optional[int] = None
    limit: Optional[int] = 100
>>>>>>> origin/main
=======
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = "default"

class ModelUnloadRequest(BaseModel):
    force: bool = False

class TokenUsageRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    model_id: Optional[str] = None
    days: Optional[int] = None
    limit: Optional[int] = 100
>>>>>>> origin/main
=======
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = "default"

class ModelUnloadRequest(BaseModel):
    force: bool = False

class TokenUsageRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    model_id: Optional[str] = None
    days: Optional[int] = None
    limit: Optional[int] = 100
>>>>>>> origin/main

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

@app.get("/v1/status")
async def get_status():
    """Get detailed system status and resource usage."""
    try:
        status = manager.get_resource_status()
        status["server_status"] = "healthy"
        return status
    except Exception as e:
        logging.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/status")
async def get_status():
    """Get detailed system status and resource usage."""
    try:
        status = manager.get_resource_status()
        status["server_status"] = "healthy"
        return status
    except Exception as e:
        logging.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/status")
async def get_status():
    """Get detailed system status and resource usage."""
    try:
        status = manager.get_resource_status()
        status["server_status"] = "healthy"
        return status
    except Exception as e:
        logging.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint with enhanced metadata."""
    try:
        models = manager.list_models()
        return {"object": "list", "data": models}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
@app.post("/v1/model/unload")
async def unload_model(request: ModelUnloadRequest):
    """Unload the currently loaded model."""
    try:
        manager.unload_model()
        return {"message": "Model unloaded successfully"}
    except Exception as e:
        logging.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/model/reload")
async def reload_model():
    """Reload model from registry."""
    try:
        manager.reload_model()
        return {"message": "Model reload initiated"}
    except Exception as e:
        logging.error(f"Error reloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tokens/usage")
async def get_token_usage(request: TokenUsageRequest):
    """Get token usage history."""
    try:
        db = get_token_database()
        
        # Build filters
        start_date = None
        if request.days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=request.days)
        
        history = db.get_usage_history(
            limit=request.limit or 100,
            model_id=request.model_id,
            session_id=request.session_id,
            user_id=request.user_id,
            start_date=start_date
        )
        
        return {
            "usage": [usage.__dict__ for usage in history],
            "count": len(history)
        }
    except Exception as e:
        logging.error(f"Error getting token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/summary")
async def get_token_summary(
    period: str = "day",
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get token usage summary."""
    try:
        db = get_token_database()
        summary = db.get_usage_summary(period=period, model_id=model, user_id=user)
        return summary
    except Exception as e:
        logging.error(f"Error getting token summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/stats")
async def get_token_stats(
    days: int = 30,
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get detailed token statistics."""
    try:
        db = get_token_database()
        
        # Get data for the period
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        history = db.get_usage_history(
            limit=10000,  # Large limit for analytics
            start_date=start_date,
            model_id=model,
            user_id=user
        )
        
        if not history:
            return {"message": "No usage data found"}
        
        # Calculate statistics
        total_requests = len(history)
        total_tokens = sum(h.total_tokens for h in history)
        total_cost = sum(h.cost_usd for h in history)
        
        # Daily averages
        avg_daily_requests = total_requests / days
        avg_daily_tokens = total_tokens / days
        avg_daily_cost = total_cost / days
        
        # Model breakdown
        model_stats = {}
        for usage in history:
            if usage.model_id not in model_stats:
                model_stats[usage.model_id] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            model_stats[usage.model_id]["requests"] += 1
            model_stats[usage.model_id]["tokens"] += usage.total_tokens
            model_stats[usage.model_id]["cost"] += usage.cost_usd
        
        return {
            "period_days": days,
            "total": {
                "requests": total_requests,
                "tokens": total_tokens,
                "cost_usd": total_cost,
                "avg_daily_requests": avg_daily_requests,
                "avg_daily_tokens": avg_daily_tokens,
                "avg_daily_cost": avg_daily_cost
            },
            "by_model": model_stats
        }
    except Exception as e:
        logging.error(f"Error getting token stats: {e}")
>>>>>>> origin/main
=======
@app.post("/v1/model/unload")
async def unload_model(request: ModelUnloadRequest):
    """Unload the currently loaded model."""
    try:
        manager.unload_model()
        return {"message": "Model unloaded successfully"}
    except Exception as e:
        logging.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/model/reload")
async def reload_model():
    """Reload model from registry."""
    try:
        manager.reload_model()
        return {"message": "Model reload initiated"}
    except Exception as e:
        logging.error(f"Error reloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tokens/usage")
async def get_token_usage(request: TokenUsageRequest):
    """Get token usage history."""
    try:
        db = get_token_database()
        
        # Build filters
        start_date = None
        if request.days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=request.days)
        
        history = db.get_usage_history(
            limit=request.limit or 100,
            model_id=request.model_id,
            session_id=request.session_id,
            user_id=request.user_id,
            start_date=start_date
        )
        
        return {
            "usage": [usage.__dict__ for usage in history],
            "count": len(history)
        }
    except Exception as e:
        logging.error(f"Error getting token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/summary")
async def get_token_summary(
    period: str = "day",
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get token usage summary."""
    try:
        db = get_token_database()
        summary = db.get_usage_summary(period=period, model_id=model, user_id=user)
        return summary
    except Exception as e:
        logging.error(f"Error getting token summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/stats")
async def get_token_stats(
    days: int = 30,
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get detailed token statistics."""
    try:
        db = get_token_database()
        
        # Get data for the period
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        history = db.get_usage_history(
            limit=10000,  # Large limit for analytics
            start_date=start_date,
            model_id=model,
            user_id=user
        )
        
        if not history:
            return {"message": "No usage data found"}
        
        # Calculate statistics
        total_requests = len(history)
        total_tokens = sum(h.total_tokens for h in history)
        total_cost = sum(h.cost_usd for h in history)
        
        # Daily averages
        avg_daily_requests = total_requests / days
        avg_daily_tokens = total_tokens / days
        avg_daily_cost = total_cost / days
        
        # Model breakdown
        model_stats = {}
        for usage in history:
            if usage.model_id not in model_stats:
                model_stats[usage.model_id] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            model_stats[usage.model_id]["requests"] += 1
            model_stats[usage.model_id]["tokens"] += usage.total_tokens
            model_stats[usage.model_id]["cost"] += usage.cost_usd
        
        return {
            "period_days": days,
            "total": {
                "requests": total_requests,
                "tokens": total_tokens,
                "cost_usd": total_cost,
                "avg_daily_requests": avg_daily_requests,
                "avg_daily_tokens": avg_daily_tokens,
                "avg_daily_cost": avg_daily_cost
            },
            "by_model": model_stats
        }
    except Exception as e:
        logging.error(f"Error getting token stats: {e}")
>>>>>>> origin/main
=======
@app.post("/v1/model/unload")
async def unload_model(request: ModelUnloadRequest):
    """Unload the currently loaded model."""
    try:
        manager.unload_model()
        return {"message": "Model unloaded successfully"}
    except Exception as e:
        logging.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/model/reload")
async def reload_model():
    """Reload model from registry."""
    try:
        manager.reload_model()
        return {"message": "Model reload initiated"}
    except Exception as e:
        logging.error(f"Error reloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tokens/usage")
async def get_token_usage(request: TokenUsageRequest):
    """Get token usage history."""
    try:
        db = get_token_database()
        
        # Build filters
        start_date = None
        if request.days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=request.days)
        
        history = db.get_usage_history(
            limit=request.limit or 100,
            model_id=request.model_id,
            session_id=request.session_id,
            user_id=request.user_id,
            start_date=start_date
        )
        
        return {
            "usage": [usage.__dict__ for usage in history],
            "count": len(history)
        }
    except Exception as e:
        logging.error(f"Error getting token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/summary")
async def get_token_summary(
    period: str = "day",
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get token usage summary."""
    try:
        db = get_token_database()
        summary = db.get_usage_summary(period=period, model_id=model, user_id=user)
        return summary
    except Exception as e:
        logging.error(f"Error getting token summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tokens/stats")
async def get_token_stats(
    days: int = 30,
    model: Optional[str] = None,
    user: Optional[str] = None
):
    """Get detailed token statistics."""
    try:
        db = get_token_database()
        
        # Get data for the period
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        history = db.get_usage_history(
            limit=10000,  # Large limit for analytics
            start_date=start_date,
            model_id=model,
            user_id=user
        )
        
        if not history:
            return {"message": "No usage data found"}
        
        # Calculate statistics
        total_requests = len(history)
        total_tokens = sum(h.total_tokens for h in history)
        total_cost = sum(h.cost_usd for h in history)
        
        # Daily averages
        avg_daily_requests = total_requests / days
        avg_daily_tokens = total_tokens / days
        avg_daily_cost = total_cost / days
        
        # Model breakdown
        model_stats = {}
        for usage in history:
            if usage.model_id not in model_stats:
                model_stats[usage.model_id] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            model_stats[usage.model_id]["requests"] += 1
            model_stats[usage.model_id]["tokens"] += usage.total_tokens
            model_stats[usage.model_id]["cost"] += usage.cost_usd
        
        return {
            "period_days": days,
            "total": {
                "requests": total_requests,
                "tokens": total_tokens,
                "cost_usd": total_cost,
                "avg_daily_requests": avg_daily_requests,
                "avg_daily_tokens": avg_daily_tokens,
                "avg_daily_cost": avg_daily_cost
            },
            "by_model": model_stats
        }
    except Exception as e:
        logging.error(f"Error getting token stats: {e}")
>>>>>>> origin/main
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """OpenAI-compatible completions endpoint."""
    try:
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
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
=======
        # Extract generation parameters
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_new_tokens"] = request.max_tokens
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.top_k is not None:
            kwargs["top_k"] = request.top_k
        
        # Add tracking parameters
        kwargs["session_id"] = request.session_id or str(uuid.uuid4())
        kwargs["user_id"] = request.user_id or "default"
        kwargs["request_start_time"] = datetime.utcnow()
        
        response = await manager.get_response(
            model_id=request.model,
            messages=[m.model_dump() for m in request.messages],
            **kwargs
        )
        return response
>>>>>>> origin/main
=======
        # Extract generation parameters
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_new_tokens"] = request.max_tokens
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.top_k is not None:
            kwargs["top_k"] = request.top_k
        
        # Add tracking parameters
        kwargs["session_id"] = request.session_id or str(uuid.uuid4())
        kwargs["user_id"] = request.user_id or "default"
        kwargs["request_start_time"] = datetime.utcnow()
        
        response = await manager.get_response(
            model_id=request.model,
            messages=[m.model_dump() for m in request.messages],
            **kwargs
        )
        return response
>>>>>>> origin/main
=======
        # Extract generation parameters
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_new_tokens"] = request.max_tokens
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.top_k is not None:
            kwargs["top_k"] = request.top_k
        
        # Add tracking parameters
        kwargs["session_id"] = request.session_id or str(uuid.uuid4())
        kwargs["user_id"] = request.user_id or "default"
        kwargs["request_start_time"] = datetime.utcnow()
        
        response = await manager.get_response(
            model_id=request.model,
            messages=[m.model_dump() for m in request.messages],
            **kwargs
        )
        return response
>>>>>>> origin/main
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
