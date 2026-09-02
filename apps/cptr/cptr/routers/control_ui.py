"""Read-only CPTR Control API snapshot for the ChatGPT Workbench UI.

This endpoint deliberately lives under /api/control/v1 instead of reusing the
browser/admin cookie APIs. It exposes only bounded, non-secret summary data to
an already-scoped CPTR service token; all mutations continue through dedicated
Control API/MCP actions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from cptr.models import Config
from cptr.routers.control import list_models, list_workspaces
from cptr.services.coding_benchmark import coding_benchmark_store
from cptr.services.control_auth import authenticate_control_request
from cptr.services.mcp_usage_store import mcp_usage_store
from cptr.services.runtime_metrics import runtime_metrics
from cptr.utils.db import database_ready

router = APIRouter(prefix="/ui", tags=["control-ui"])


def _safe_mcp_servers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    servers: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        server_type = str(item.get("type") or "openapi")
        if server_type not in {"mcp", "mcp_stdio"}:
            continue
        servers.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "type": server_type,
                "enabled": bool(item.get("enabled", True)),
            }
        )
    return servers


@router.get("/overview")
async def get_ui_overview(request: Request):
    """Return the bounded read-only snapshot used by the ChatGPT Workbench."""

    # Reuse the canonical scoped Control API readers so this aggregate endpoint
    # requires both workspace and task read authority and preserves user scoping.
    workspace_payload = await list_workspaces(request, include_unavailable=True)
    model_payload = await list_models(request)
    owner_id = await authenticate_control_request(request, "task:read")
    usage_summary = await mcp_usage_store.summary(owner_id)
    engineering = await mcp_usage_store.engineering_sessions(owner_id, limit=20)
    coding_benchmark = await coding_benchmark_store.leaderboard(owner_id)

    try:
        db_ready = bool(await database_ready())
    except Exception:
        db_ready = False

    metrics = runtime_metrics.snapshot()
    raw_servers = await Config.get("tool_servers")
    servers = _safe_mcp_servers(raw_servers)
    workspaces = list(workspace_payload.get("workspaces") or [])
    models = list(model_payload.get("models") or [])
    default_model = next(
        (str(model.get("model_id")) for model in models if isinstance(model, dict) and model.get("default")),
        None,
    )

    return {
        "status": "ok" if db_ready else "degraded",
        "system": {
            "database": "ok" if db_ready else "error",
            "uptime_seconds": int(metrics.get("uptime_seconds") or 0),
            "requests": metrics.get("requests") or {},
            "database_metrics": metrics.get("database") or {},
            "event_loop": metrics.get("event_loop") or {},
            "process": metrics.get("process") or {},
        },
        "workspaces": {
            "count": len(workspaces),
            "available": sum(1 for item in workspaces if isinstance(item, dict) and item.get("available")),
            "items": workspaces,
        },
        "models": {
            "count": len(models),
            "default_model": default_model,
            "items": models,
        },
        "mcp_servers": {
            "count": len(servers),
            "connected_configurations": servers,
        },
        "mcp_usage": usage_summary,
        "engineering": engineering,
        "coding_benchmark": coding_benchmark,
        "api_surface": {
            "source": "heidi-dang/computer@a4a3a02251312e5f5c04b910d1e11857323b0ab5",
            "families": [
                "system",
                "mcp",
                "workspace",
                "terminal",
                "browser",
                "automations",
                "skills",
                "memory",
                "search",
                "chat",
                "gateway",
            ],
        },
    }
