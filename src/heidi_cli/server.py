from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .shared.config import ConfigLoader

app = FastAPI(title="Heidi Learning Suite API")

# Load suite config
suite_config = ConfigLoader.load()

# CORS allowlist from config or env
_cors_env = os.getenv("HEIDI_CORS_ORIGINS", "").strip()
if _cors_env:
    ALLOW_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    ALLOW_ORIGINS = ["*"] # Default to open for internal suite development

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "heidi-learning-suite"}

# Placeholder for OpenAI Compatibility Layer (Module 1)
# These will be implemented in Phase 1
@app.get("/v1/models")
async def list_models():
    # To be implemented in Phase 1
    return {"object": "list", "data": []}

@app.post("/v1/chat/completions")
async def chat_completions():
    # To be implemented in Phase 1
    raise HTTPException(status_code=501, detail="Not implemented yet")
