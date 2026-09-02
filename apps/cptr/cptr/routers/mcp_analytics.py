"""Owner-scoped MCP usage persistence and engineering-session analytics."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from cptr.services.control_auth import authenticate_control_request
from cptr.services.mcp_usage_models import McpUsageDiagnostic
from cptr.services.mcp_usage_store import mcp_usage_store

router = APIRouter(prefix="/api/control/v1/mcp/analytics", tags=["mcp-analytics"])


async def _user(request: Request, scope: str) -> str:
    try:
        return await authenticate_control_request(request, scope)
    except PermissionError as exc:
        message = str(exc)
        raise HTTPException(
            status_code=403 if message.startswith("missing required scope") else 401,
            detail="control-plane access denied",
        ) from exc


@router.post("/usage/events")
async def ingest_usage_event(request: Request, body: McpUsageDiagnostic):
    """Persist one bounded MCP-visible usage event idempotently by event ID."""

    owner_id = await _user(request, "task:write")
    accepted = await mcp_usage_store.ingest(owner_id, [body])
    was_accepted = body.event_id in accepted
    return {
        "event_id": body.event_id,
        "accepted": was_accepted,
        "duplicate": not was_accepted,
    }


@router.get("/usage/summary")
async def get_usage_summary(request: Request):
    """Return durable current-week/current-month/rolling/all-time MCP usage totals."""

    owner_id = await _user(request, "task:read")
    return await mcp_usage_store.summary(owner_id)


@router.get("/engineering/sessions")
async def get_engineering_sessions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return payload-free observed real-work metrics; these are not comparable benchmarks."""

    owner_id = await _user(request, "task:read")
    return await mcp_usage_store.engineering_sessions(owner_id, limit=limit)
