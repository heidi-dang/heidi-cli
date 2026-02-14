from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
import uvicorn

from .auth_db import init_db
from .auth_middleware import AuthMiddleware
from .orchestrator.planner import PlannerAgent
from .orchestrator.session import Session

# Optional API key protection:
# - If HEIDI_API_KEY is set, protected endpoints require:
#     X-Heidi-Key: <key>
# - Streaming via EventSource can't send custom headers, so /stream also accepts:
#     ?key=<key>   (MVP tradeoff; can be replaced with fetch() streaming in UI later)
HEIDI_API_KEY = os.getenv("HEIDI_API_KEY", "").strip()

# CORS allowlist:
# - If HEIDI_CORS_ORIGINS is set (comma-separated), it overrides everything.
# - Otherwise defaults to localhost UI origins for development.
# Note: With credentials (cookies), browsers reject wildcard "*" origins.
_cors_env = os.getenv("HEIDI_CORS_ORIGINS", "").strip()
if _cors_env:
    ALLOW_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    ALLOW_ORIGINS = [
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app = FastAPI(title="Heidi CLI Server")


# UI distribution directory - check multiple locations
def _get_ui_dist() -> Optional[Path]:
    # 1. HEIDI_UI_DIST env var
    env_path = os.getenv("HEIDI_UI_DIST")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # 2. HEIDI_HOME/ui/dist
    heidi_home = os.getenv("HEIDI_HOME")
    if heidi_home:
        p = Path(heidi_home) / "ui" / "dist"
        if p.exists():
            return p

    # 3. XDG_CACHE_HOME/heidi/ui/dist
    xdg_cache = os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    p = Path(xdg_cache) / "heidi" / "ui" / "dist"
    if p.exists():
        return p

    # 4. Fallback: bundled ui_dist (for local dev)
    bundled = Path(__file__).parent / "ui_dist"
    if bundled.exists():
        return bundled

    return None


UI_DIST = _get_ui_dist()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Heidi-Key",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
)

app.add_middleware(AuthMiddleware)

init_db()

# Global Session Manager
ACTIVE_SESSIONS: dict[str, PlannerAgent] = {}


def get_planner(session_id: str = "default") -> PlannerAgent:
    if session_id not in ACTIVE_SESSIONS:
        session = Session.load(session_id)
        if not session:
            session = Session(session_id=session_id)
            session.save()
        ACTIVE_SESSIONS[session_id] = PlannerAgent(session)
    return ACTIVE_SESSIONS[session_id]


def _check_auth(request: Request, stream_key: Optional[str] = None) -> bool:
    """Check if request is authorized via session OR API key.

    Returns True if authorized, False otherwise.
    """
    if hasattr(request.state, "user") and request.state.user is not None:
        return True

    if not HEIDI_API_KEY:
        return False

    header_key = request.headers.get("x-heidi-key", "")
    effective = (header_key or stream_key or "").strip()
    return bool(effective and effective == HEIDI_API_KEY)


def _require_api_key(request: Request, stream_key: Optional[str] = None) -> None:
    if not HEIDI_API_KEY:
        return
    if not _check_auth(request, stream_key):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
async def root():
    """Redirect root to /ui/ for the UI"""
    if UI_DIST and UI_DIST.exists():
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/ui/")
    return {"status": "ok", "service": "heidi-cli", "ui": "visit /ui for the web interface"}


@app.get("/ui")
async def ui_index():
    """Redirect /ui to /ui/ for proper SPA routing"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/ui/")


@app.get("/ui/{path:path}")
async def serve_ui(path: str):
    """Serve UI static files from ui_dist"""
    if not UI_DIST or not UI_DIST.exists():
        return HTMLResponse(
            "<html><body><h1>UI Not Built</h1><p>Run <code>heidi ui build</code> to build the UI.</p></body></html>",
            status_code=200,
        )

    file_path = UI_DIST / path
    if file_path.is_file():
        from starlette.responses import FileResponse

        return FileResponse(file_path)

    index_path = UI_DIST / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())

    return HTMLResponse(
        "<html><body><h1>404</h1><p>File not found</p></body></html>",
        status_code=404,
    )


@app.get("/agents")
async def list_agents():
    from .orchestrator.registry import AgentRegistry

    agents = AgentRegistry.list_agents()
    return [{"name": name, "description": desc} for name, desc in agents]


@app.get("/models")
async def list_models():
    """List available Copilot models."""
    from .copilot_runtime import list_copilot_models

    try:
        models = await list_copilot_models()
        return models
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/runs")
async def list_runs(limit: int = 10, request: Request = None):
    if request is not None:
        _require_api_key(request)
    from .config import ConfigManager

    runs_dir = ConfigManager.runs_dir()
    if not runs_dir.exists():
        return []

    runs = []
    for run_path in sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[
        :limit
    ]:
        run_json = run_path / "run.json"
        if run_json.exists():
            meta = json.loads(run_json.read_text())
            runs.append(
                {
                    "run_id": run_path.name,
                    "status": meta.get("status", "unknown"),
                    "task": meta.get("task", meta.get("prompt", "")),
                    "executor": meta.get("executor", ""),
                }
            )

    return runs


@app.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request):
    _require_api_key(request)
    from .config import ConfigManager

    run_dir = ConfigManager.runs_dir() / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    run_json = run_dir / "run.json"
    transcript = run_dir / "transcript.jsonl"

    result = {"run_id": run_id}

    if run_json.exists():
        result["meta"] = json.loads(run_json.read_text())

    if transcript.exists():
        events = []
        for line in transcript.read_text().strip().split("\n"):
            if line:
                raw = json.loads(line)
                event = {
                    "type": raw.get("type", ""),
                    "ts": raw.get("timestamp", ""),
                    "message": raw.get("data", {}).get("message", ""),
                    "details": raw.get("data", {}),
                }
                events.append(event)
        result["events"] = events

    return result


@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request, key: Optional[str] = None):
    _require_api_key(request, stream_key=key)
    from .config import ConfigManager

    run_dir = ConfigManager.runs_dir() / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        transcript = run_dir / "transcript.jsonl"
        if not transcript.exists():
            return

        last_pos = 0
        while True:
            await asyncio.sleep(1)
            content = transcript.read_text()
            if len(content) > last_pos:
                new_content = content[last_pos:]
                last_pos = len(content)
                for line in new_content.strip().split("\n"):
                    if line:
                        yield f"data: {line}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_no_store_headers(),
    )


def _no_store_headers() -> dict:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, request: Request):
    _require_api_key(request)
    from .config import ConfigManager
    from .logging import HeidiLogger

    run_dir = ConfigManager.runs_dir() / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    run_json = run_dir / "run.json"
    if run_json.exists():
        meta = json.loads(run_json.read_text())
        if meta.get("status") in ["completed", "failed", "cancelled"]:
            return {"status": "already_terminal", "run_id": run_id}

    import uuid

    cancel_id = str(uuid.uuid4())[:8]
    HeidiLogger.write_run_meta(
        {
            "status": "cancelled",
            "cancelled_at": str(asyncio.get_event_loop().time()),
        }
    )

    cancel_marker = run_dir / "cancelled"
    cancel_marker.write_text(cancel_id)

    return {"status": "cancelled", "run_id": run_id}


class RunRequest(BaseModel):
    prompt: str
    executor: str = "copilot"
    model: Optional[str] = None
    workdir: Optional[str] = None


class LoopRequest(BaseModel):
    task: str
    executor: str = "copilot"
    model: Optional[str] = None
    max_retries: int = 2
    workdir: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    executor: str = "copilot"


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """Stateful chat endpoint using PlannerAgent."""
    try:
        # Determine session ID (use user ID if auth enabled, else default)
        session_id = "default"
        if hasattr(http_request.state, "user") and http_request.state.user:
            session_id = http_request.state.user.id

        planner = get_planner(session_id)
        workdir = Path.cwd()
        response = await planner.process_user_message(request.message, workdir)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history")
async def chat_history(http_request: Request):
    """Get conversation history for current session."""
    session_id = "default"
    if hasattr(http_request.state, "user") and http_request.state.user:
        session_id = http_request.state.user.id

    planner = get_planner(session_id)
    return planner.session.history


@app.post("/plan/approve")
async def approve_plan(http_request: Request):
    """Approve current plan and start execution."""
    session_id = "default"
    if hasattr(http_request.state, "user") and http_request.state.user:
        session_id = http_request.state.user.id

    planner = get_planner(session_id)
    workdir = Path.cwd()
    result = await planner.approve_plan(workdir)
    return {"status": "ok", "message": result}


@app.post("/plan/reject")
async def reject_plan(http_request: Request, reason: str = "Rejected by user"):
    """Reject current plan."""
    session_id = "default"
    if hasattr(http_request.state, "user") and http_request.state.user:
        session_id = http_request.state.user.id

    planner = get_planner(session_id)
    workdir = Path.cwd()
    result = await planner.reject_plan(reason, workdir)
    return {"status": "ok", "message": result}


@app.get("/session")
async def get_session(http_request: Request):
    """Get current session state."""
    session_id = "default"
    if hasattr(http_request.state, "user") and http_request.state.user:
        session_id = http_request.state.user.id

    planner = get_planner(session_id)
    return {
        "session_id": planner.session.session_id,
        "state": planner.session.state,
        "task": planner.session.task,
        "plan": planner.session.plan,
        "task_slug": planner.session.task_slug,
    }


@app.post("/run", response_model=RunResponse)
async def run(request: RunRequest, http_request: Request):
    _require_api_key(http_request)
    from .logging import HeidiLogger
    from .orchestrator.loop import pick_executor

    workdir = Path(request.workdir) if request.workdir else None
    if not workdir:
        workdir = Path.cwd()

    run_id = HeidiLogger.init_run()
    HeidiLogger.write_run_meta(
        {
            "run_id": run_id,
            "prompt": request.prompt,
            "executor": request.executor,
            "workdir": str(workdir),
            "status": "running",
        }
    )

    try:
        executor = pick_executor(request.executor, model=request.model)
        result = await executor.run(request.prompt, workdir)
        HeidiLogger.write_run_meta(
            {"status": "completed", "ok": result.ok, "result": result.output}
        )
        return RunResponse(run_id=run_id, status="completed", result=result.output)
    except Exception as e:
        HeidiLogger.write_run_meta({"status": "failed", "error": str(e)})
        return RunResponse(run_id=run_id, status="failed", error=str(e))


@app.post("/loop", response_model=RunResponse)
async def loop(request: LoopRequest, http_request: Request):
    _require_api_key(http_request)
    from .logging import HeidiLogger
    from .orchestrator.loop import run_loop

    workdir = Path(request.workdir) if request.workdir else None
    if not workdir:
        workdir = Path.cwd()

    run_id = HeidiLogger.init_run()
    HeidiLogger.write_run_meta(
        {
            "run_id": run_id,
            "task": request.task,
            "executor": request.executor,
            "max_retries": request.max_retries,
            "workdir": str(workdir),
            "status": "running",
        }
    )

    async def _loop_background():
        try:
            result = await run_loop(
                task=request.task,
                executor=request.executor,
                model=request.model,
                max_retries=request.max_retries,
                workdir=workdir,
            )
            HeidiLogger.write_run_meta({"status": "completed", "result": result})
        except Exception as e:
            HeidiLogger.write_run_meta({"status": "failed", "error": str(e)})

    asyncio.create_task(_loop_background())
    return RunResponse(run_id=run_id, status="running")


# API Aliases - UI served by backend uses /api/* prefix
@app.get("/api/health")
async def api_health():
    return await health()


@app.get("/api/agents")
async def api_list_agents():
    from .orchestrator.registry import AgentRegistry

    agents = AgentRegistry.list_agents()
    return [{"name": name, "description": desc} for name, desc in agents]


@app.post("/api/run")
async def api_run(request: RunRequest, http_request: Request):
    return await run(request, http_request)


@app.post("/api/loop")
async def api_loop(request: LoopRequest, http_request: Request):
    return await loop(request, http_request)


@app.post("/api/chat")
async def api_chat(request: ChatRequest, http_request: Request):
    return await chat(request, http_request)


@app.get("/api/chat/history")
async def api_chat_history(http_request: Request):
    return await chat_history(http_request)


@app.post("/api/plan/approve")
async def api_approve_plan(http_request: Request):
    return await approve_plan(http_request)


@app.get("/api/tasks/{slug}")
async def api_get_task_artifacts(slug: str):
    from .orchestrator.artifacts import TaskArtifact

    artifact = TaskArtifact.load(slug)
    if not artifact:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "slug": artifact.slug,
        "content": artifact.content,
        "audit": artifact.audit_content,
        "status": artifact.status,
    }


@app.get("/api/runs")
async def api_list_runs(limit: int = 10, request: Request = None):
    return await list_runs(limit, request)


@app.get("/api/runs/{run_id}")
async def api_get_run(run_id: str, request: Request):
    return await get_run(run_id, request)


@app.get("/api/runs/{run_id}/stream")
async def api_stream_run(run_id: str, request: Request, key: Optional[str] = None):
    return await stream_run(run_id, request, key)


@app.post("/api/runs/{run_id}/cancel")
async def api_cancel_run(run_id: str, request: Request):
    return await cancel_run(run_id, request)


# ==================== OpenAI-Compatible Endpoints ====================


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None


@app.get("/v1/models")
async def list_models_v1():
    """OpenAI-compatible /v1/models endpoint."""
    from .copilot_runtime import list_copilot_models

    models = []
    ts = int(datetime.now(timezone.utc).timestamp())

    try:
        copilot_models = await list_copilot_models()
        for m in copilot_models:
            mid = m.get("id") or m.get("name", "")
            if mid and not mid.startswith("error"):
                models.append(
                    {
                        "id": f"copilot/{mid}",
                        "object": "model",
                        "created": ts,
                        "owned_by": "github/copilot",
                    }
                )
    except Exception:
        pass

    if not models:
        for m in ["gpt-5", "claude-sonnet-4-20250514", "gpt-4o", "o3"]:
            models.append(
                {
                    "id": f"copilot/{m}",
                    "object": "model",
                    "created": ts,
                    "owned_by": "github/copilot",
                }
            )

    models.append(
        {
            "id": "jules/default",
            "object": "model",
            "created": ts,
            "owned_by": "google/jules",
        }
    )

    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """OpenAI-compatible /v1/chat/completions endpoint."""
    from .orchestrator.loop import pick_executor
    from .logging import HeidiLogger
    from .copilot_runtime import CopilotRuntime

    model_id = request.model
    executor_name = "copilot"
    actual_model = None

    if "/" in model_id:
        prefix, actual_model = model_id.split("/", 1)
        if prefix == "jules":
            executor_name = "jules"
        elif prefix == "opencode":
            executor_name = "opencode"
        elif prefix == "ollama":
            executor_name = "ollama"

    prompt = "\n".join([f"{m.role}: {m.content}" for m in request.messages])
    ts = int(datetime.now(timezone.utc).timestamp())

    if request.stream:

        async def generate():
            try:
                executor = pick_executor(executor_name, model=actual_model)
                workdir = Path.cwd()
                run_id = HeidiLogger.init_run()

                if executor_name == "copilot":
                    rt = CopilotRuntime(model=actual_model, cwd=workdir)
                    await rt.start()
                    try:
                        session = await rt.client.create_session({"model": actual_model or "gpt-5"})
                        queue = asyncio.Queue()
                        done = asyncio.Event()

                        def on_event(event):
                            t = getattr(getattr(event, "type", None), "value", None) or getattr(
                                event, "type", None
                            )
                            if t == "assistant.message":
                                content = getattr(getattr(event, "data", None), "content", None)
                                if content:
                                    chunk = {
                                        "id": f"chatcmpl-{run_id[:8]}",
                                        "object": "chat.completion.chunk",
                                        "created": ts,
                                        "model": request.model,
                                        "choices": [
                                            {
                                                "index": 0,
                                                "delta": {"content": content},
                                                "finish_reason": None,
                                            }
                                        ],
                                    }
                                    queue.put_nowait(f"data: {json.dumps(chunk)}\n\n")
                            elif t == "session.idle":
                                done.set()
                            elif t == "session.error":
                                error_msg = getattr(getattr(event, "data", None), "message", "Unknown error")
                                queue.put_nowait(f"data: {json.dumps({'error': {'message': error_msg}})}\n\n")
                                done.set()

                        session.on(on_event)
                        asyncio.create_task(session.send({"prompt": prompt}))

                        while not done.is_set():
                            try:
                                chunk = await asyncio.wait_for(queue.get(), timeout=1.0)
                                yield chunk
                            except asyncio.TimeoutError:
                                if done.is_set():
                                    break
                                continue

                        while not queue.empty():
                            yield queue.get_nowait()

                        yield "data: [DONE]\n\n"
                    finally:
                        await rt.stop()
                else:
                    result = await executor.run(prompt, workdir)
                    content = result.output if hasattr(result, "output") else str(result)
                    chunk = {
                        "id": f"chatcmpl-{run_id[:8]}",
                        "object": "chat.completion.chunk",
                        "created": ts,
                        "model": request.model,
                        "choices": [
                            {"index": 0, "delta": {"content": content}, "finish_reason": "stop"}
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        executor = pick_executor(executor_name, model=actual_model)
        workdir = Path.cwd()
        result = await executor.run(prompt, workdir)

        response = {
            "id": f"chatcmpl-{HeidiLogger.init_run()[:8]}",
            "object": "chat.completion",
            "created": ts,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.output if hasattr(result, "output") else str(result),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 0,
                "total_tokens": len(prompt.split()),
            },
        }
        return response
    except Exception as e:
        return {"error": {"message": str(e), "type": "invalid_request_error"}}


def start_server(host: str = "0.0.0.0", port: int = 7777):
    uvicorn.run(app, host=host, port=port)


@app.get("/auth/login/{provider}")
async def auth_login(provider: str):
    """Initiate OAuth login."""
    from .auth_oauth import create_github_auth_url

    if provider != "github":
        raise HTTPException(status_code=400, detail="Unsupported provider")

    auth_url, state = create_github_auth_url()
    return {"auth_url": auth_url, "state": state}


@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str, code: str, state: str):
    """OAuth callback handler."""
    from .auth_oauth import complete_github_login

    if provider != "github":
        raise HTTPException(status_code=400, detail="Unsupported provider")

    result = await complete_github_login(code, state)
    if not result:
        raise HTTPException(status_code=400, detail="Login failed")

    response = RedirectResponse(url="/ui/?logged_in=true")
    response.set_cookie(
        key="heidi_session",
        value=result["session_id"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@app.post("/auth/logout")
async def auth_logout(request: Request):
    """Logout endpoint."""
    session_id = request.cookies.get("heidi_session")
    if session_id:
        from .auth_oauth import logout_session

        logout_session(session_id)

    redirect_url = request.query_params.get("redirect", "/")
    redirect_response = RedirectResponse(url=redirect_url)
    redirect_response.delete_cookie("heidi_session")
    return redirect_response


@app.get("/auth/me")
async def auth_me(request: Request):
    """Get current user."""
    if request.state.user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "id": request.state.user.id,
        "email": request.state.user.email,
        "name": request.state.user.name,
        "avatar_url": request.state.user.avatar_url,
    }


@app.get("/auth/status")
async def auth_status(request: Request):
    """Get auth status."""
    return {
        "authenticated": request.state.user is not None,
        "user": {
            "id": request.state.user.id,
            "email": request.state.user.email,
            "name": request.state.user.name,
            "avatar_url": request.state.user.avatar_url,
        }
        if request.state.user
        else None,
    }


# UI calls /api/* only - add aliases for OpenCode endpoints
@app.get("/api/connect/opencode/openai/status")
async def api_opencode_openai_status():
    """Alias for /connect/opencode/openai/status (UI compatibility)."""
    return await opencode_openai_status()


@app.post("/api/connect/opencode/openai/test")
async def api_opencode_openai_test():
    """Alias for /connect/opencode/openai/test (UI compatibility)."""
    return await opencode_openai_test()


@app.get("/connect/opencode/openai/status")
async def opencode_openai_status():
    """Check OpenCode OpenAI connection status for UI."""
    import os
    import shutil
    from pathlib import Path

    opencode_path = shutil.which("opencode")
    if not opencode_path:
        return {
            "connected": False,
            "error": "OpenCode CLI not installed",
            "authPath": None,
            "models": [],
        }

    if os.name == "nt":
        user_profile = os.environ.get("USERPROFILE", "")
        auth_path = Path(user_profile) / ".local" / "share" / "opencode" / "auth.json"
    else:
        auth_path = Path.home() / ".local" / "share" / "opencode" / "auth.json"

    if not auth_path.exists():
        return {
            "connected": False,
            "error": "OpenCode auth not found. Run 'heidi connect opencode openai'",
            "authPath": str(auth_path),
            "models": [],
        }

    import subprocess

    try:
        result = subprocess.run(
            ["opencode", "models", "openai"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            models = [line.strip() for line in lines if line.strip()]
            return {
                "connected": True,
                "error": None,
                "authPath": str(auth_path),
                "models": models,
            }
        return {
            "connected": False,
            "error": "OpenAI not connected",
            "authPath": str(auth_path),
            "models": [],
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "authPath": str(auth_path),
            "models": [],
        }


@app.post("/connect/opencode/openai/test")
async def opencode_openai_test():
    """Test OpenCode OpenAI connection."""
    import subprocess

    try:
        result = subprocess.run(
            ["opencode", "models", "openai"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {"pass": False, "error": "No OpenAI models", "output": ""}

        lines = result.stdout.strip().split("\n")
        models = [line.strip() for line in lines if line.strip()]
        if not models:
            return {"pass": False, "error": "No models", "output": ""}

        first_model = models[0]
    except Exception as e:
        return {"pass": False, "error": str(e), "output": ""}

    try:
        result = subprocess.run(
            ["opencode", "run", "say ok", f"--model=openai/{first_model.split('/')[-1]}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return {"pass": True, "error": None, "output": result.stdout[:500]}
        return {"pass": False, "error": result.stderr[:200], "output": ""}
    except Exception as e:
        return {"pass": False, "error": str(e), "output": ""}
