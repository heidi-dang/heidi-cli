
from fastapi.testclient import TestClient
from heidi_cli.server import app

client = TestClient(app)

def test_cors_valid_request():
    """Test that valid CORS requests are accepted."""
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-heidi-key,authorization,accept,origin,x-requested-with",
        },
    )

    # This should pass (200 OK)
    assert response.status_code == 200

    # Check Allow-Origin
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    # Check Allow-Methods
    allow_methods = response.headers["access-control-allow-methods"]
    assert "*" not in allow_methods
    for method in ["GET", "POST", "OPTIONS"]:
        assert method in allow_methods

    # Check Allow-Headers
    allow_headers = response.headers["access-control-allow-headers"]
    lower_allow_headers = allow_headers.lower()
    assert "*" not in lower_allow_headers

    for header in ["content-type", "x-heidi-key", "authorization", "accept", "origin", "x-requested-with"]:
        assert header in lower_allow_headers

def test_cors_invalid_header_request():
    """Test that requesting an invalid header results in rejection or exclusion."""
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "forbidden-header",
        },
    )

    # Starlette CORSMiddleware returns 400 if a requested header is not allowed (when not using wildcard)
    if response.status_code == 200:
        # If it returns 200, it must NOT list the forbidden header
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "forbidden-header" not in allow_headers
    else:
        # 400 is also acceptable secure behavior
        assert response.status_code == 400
