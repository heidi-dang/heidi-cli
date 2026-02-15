
import sys

# Ensure pydantic is not mocked (CI Fix)
try:
    import pydantic
    from unittest.mock import MagicMock

    # If pydantic is a mock, force reload the real module
    if isinstance(pydantic, MagicMock) or hasattr(pydantic, 'mock_calls') or not hasattr(pydantic, '__file__'):
        print("DEBUG: Detected pydantic mock, attempting to reload real module...")
        if 'pydantic' in sys.modules:
            del sys.modules['pydantic']
        if 'pydantic.main' in sys.modules:
            del sys.modules['pydantic.main']
        if 'fastapi' in sys.modules:
            del sys.modules['fastapi']

        import pydantic
        print(f"DEBUG: Reloaded pydantic: {pydantic}")
except ImportError:
    pass

from fastapi.testclient import TestClient

from unittest.mock import patch
from heidi_cli.server import app

client = TestClient(app)

def test_path_traversal_blocked(tmp_path):
    """Test that path traversal attempts are blocked."""
    # Setup directories
    ui_dist = tmp_path / "ui_dist"
    ui_dist.mkdir()

    # Create a safe file
    (ui_dist / "index.html").write_text("<html>index</html>")
    (ui_dist / "style.css").write_text("body { color: red; }")

    # Create a sensitive file outside ui_dist
    sensitive_file = tmp_path / "sensitive.txt"
    sensitive_file.write_text("SECRET_PASSWORD")

    # Patch UI_DIST in the server module
    with patch("heidi_cli.server.UI_DIST", ui_dist):
        # 1. Verify valid file access
        response = client.get("/ui/style.css")
        assert response.status_code == 200
        assert response.text == "body { color: red; }"

        # 2. Verify Path Traversal (encoded to bypass client normalization)
        response = client.get("/ui/..%2Fsensitive.txt")
        assert response.status_code == 404
        assert "SECRET_PASSWORD" not in response.text

        # 3. Verify accessing file in subdirectory works
        subdir = ui_dist / "subdir"
        subdir.mkdir()
        (subdir / "script.js").write_text("console.log('hi');")

        response = client.get("/ui/subdir/script.js")
        assert response.status_code == 200
        assert response.text == "console.log('hi');"

        # 4. Verify traversal that stays inside is allowed
        # /ui/subdir/../style.css -> /ui/style.css
        response = client.get("/ui/subdir/..%2Fstyle.css")
        assert response.status_code == 200
        assert response.text == "body { color: red; }"

def test_symlink_behavior(tmp_path):
    """Test behavior with symlinks."""
    # Setup directories
    real_dist = tmp_path / "real_dist"
    real_dist.mkdir()
    (real_dist / "style.css").write_text("body { color: blue; }")

    # Create a symlink to real_dist
    ui_dist = tmp_path / "ui_dist_link"
    ui_dist.symlink_to(real_dist)

    # Create sensitive file
    sensitive = tmp_path / "sensitive.txt"
    sensitive.write_text("SECRET")

    with patch("heidi_cli.server.UI_DIST", ui_dist):
        # 1. Valid access through symlinked UI_DIST
        response = client.get("/ui/style.css")
        assert response.status_code == 200
        assert response.text == "body { color: blue; }"

        # 2. Traversal out of symlinked directory
        response = client.get("/ui/..%2Fsensitive.txt")
        assert response.status_code == 404
