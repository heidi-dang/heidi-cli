import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth_db import get_session, get_user_by_id, cleanup_expired_sessions

PUBLIC_ROUTES = [
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/ui",
    "/ui/",
]


def is_public_route(path: str) -> bool:
    """Check if route is public (doesn't require auth)."""
    if path.startswith("/auth/login") or path.startswith("/auth/callback"):
        return True
    for route in PUBLIC_ROUTES:
        if path == route or path.startswith(route + "/"):
            return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication."""

    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get("heidi_session")
        request.state.user = None
        request.state.session = None

        if session_id:
            session = get_session(session_id)
            if session:
                user = get_user_by_id(session.user_id)
                if user:
                    request.state.user = user
                    request.state.session = session

        cleanup_expired_sessions()

        if is_public_route(request.url.path):
            return await call_next(request)

        auth_mode = os.getenv("HEIDI_AUTH_MODE", "optional")

        if auth_mode == "required" and request.state.user is None:
            if request.url.path.startswith("/api/") or request.url.path in [
                "/run",
                "/loop",
                "/runs",
            ]:
                return JSONResponse({"detail": "Authentication required"}, status_code=401)

        return await call_next(request)


def require_auth(request: Request) -> dict:
    """Guard function to require authentication."""
    if request.state.user is None:
        raise Exception("Authentication required")
    return {
        "user_id": request.state.user.id,
        "email": request.state.user.email,
        "name": request.state.user.name,
    }
