import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth_db import get_session, get_user_by_id, cleanup_expired_sessions


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/auth/") or request.url.path in [
            "/",
            "/docs",
            "/openapi.json",
        ]:
            return await call_next(request)

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

        auth_mode = os.getenv("HEIDI_AUTH_MODE", "optional")

        if auth_mode == "required" and request.state.user is None:
            if request.url.path.startswith("/api/"):
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
