from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
import uvicorn

from .auth_db import init_db
from .auth_middleware import AuthMiddleware

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

# UI distribution directory - can be overridden for development
UI_DIST = Path(__file__).parent / "ui_dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

init_db()


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
    if UI_DIST.exists():
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
    if not UI_DIST.exists():
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
                events.append(json.loads(line))
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


class RunRequest(BaseModel):
    prompt: str
    executor: str = "copilot"
    workdir: Optional[str] = None


class LoopRequest(BaseModel):
    task: str
    executor: str = "copilot"
    max_retries: int = 2
    workdir: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


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
        }
    )

    try:
        executor = pick_executor(request.executor)
        result = await executor.run(request.prompt, workdir)
        HeidiLogger.write_run_meta({"status": "completed", "ok": result.ok})
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
        }
    )

    try:
        result = await run_loop(
            task=request.task,
            executor=request.executor,
            max_retries=request.max_retries,
            workdir=workdir,
        )
        HeidiLogger.write_run_meta({"status": "completed", "result": result})
        return RunResponse(run_id=run_id, status="completed", result=result)
    except Exception as e:
        HeidiLogger.write_run_meta({"status": "failed", "error": str(e)})
        return RunResponse(run_id=run_id, status="failed", error=str(e))


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
