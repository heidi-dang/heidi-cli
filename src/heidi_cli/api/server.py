"""
Heidi API Server

FastAPI server that provides unified API access to all Heidi models.
Users can authenticate with Heidi API keys and access models from any provider.
"""

import time
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .key_manager import get_api_key_manager
from .auth import get_authenticator, AuthResult
from .router import get_api_router


# Pydantic models for API requests
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model identifier (e.g., local://my-model, hf://model-name)")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    temperature: float = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Whether to stream the response")


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


# Initialize FastAPI app
app = FastAPI(
    title="Heidi API",
    description="Unified API access to all Heidi-managed models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize components
key_manager = get_api_key_manager()
authenticator = get_authenticator()
router = get_api_router()


async def authenticate_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> AuthResult:
    """Authenticate the API key."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_result = authenticator.authenticate(credentials.credentials)
    
    if not auth_result.success:
        if auth_result.rate_limited:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=auth_result.error_message or "Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return auth_result


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Heidi API",
        "version": "1.0.0",
        "description": "Unified API access to all Heidi-managed models",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "service": "heidi-api"
    }


@app.get("/v1/models")
async def list_models(auth_result: AuthResult = Depends(authenticate_api_key)):
    """List all available models."""
    try:
        models = router.list_available_models()
        
        # Flatten all models into a single list
        all_models = []
        for provider, model_list in models.items():
            for model in model_list:
                all_models.append(model)
        
        return {
            "object": "list",
            "data": all_models
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    auth_result: AuthResult = Depends(authenticate_api_key)
):
    """Create a chat completion."""
    try:
        # Convert messages to dict format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Route the request
        response = await router.route_request(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatCompletionResponse(**response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@app.get("/v1/rate-limit")
async def get_rate_limit(auth_result: AuthResult = Depends(authenticate_api_key)):
    """Get rate limit information for the current API key."""
    try:
        rate_info = authenticator.get_rate_limit_info(auth_result.api_key)
        return rate_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get rate limit: {str(e)}"
        )


@app.get("/v1/user/info")
async def get_user_info(auth_result: AuthResult = Depends(authenticate_api_key)):
    """Get user information."""
    try:
        return {
            "user_id": auth_result.api_key.user_id,
            "key_id": auth_result.api_key.key_id,
            "key_name": auth_result.api_key.name,
            "permissions": auth_result.api_key.permissions,
            "rate_limit": auth_result.api_key.rate_limit,
            "usage_count": auth_result.api_key.usage_count,
            "created_at": auth_result.api_key.created_at.isoformat(),
            "expires_at": auth_result.api_key.expires_at.isoformat() if auth_result.api_key.expires_at else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user info: {str(e)}"
        )


# Middleware for logging and analytics
@app.middleware("http")
async def add_headers_and_logging(request, call_next):
    """Add custom headers and log requests."""
    start_time = time.time()
    
    # Add custom headers
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-API-Version"] = "1.0.0"
    response.headers["X-Service"] = "Heidi API"
    
    # Log request time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
