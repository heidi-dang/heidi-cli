from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "managed-oauth-client.py"


class OAuthHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str, object, str | None]] = []
    registrations = 0
    include_management = True

    def log_message(self, *_args):
        return

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else None

    def _send_json(self, status: int, value: object):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.requests.append(("GET", self.path, None, self.headers.get("Authorization")))
        if self.path == "/metadata":
            base = f"http://127.0.0.1:{self.server.server_port}"
            return self._send_json(
                200,
                {
                    "issuer": base,
                    "authorization_endpoint": f"{base}/authorize",
                    "token_endpoint": f"{base}/token",
                    "registration_endpoint": f"{base}/register",
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                    "token_endpoint_auth_methods_supported": [
                        "client_secret_basic",
                        "client_secret_post",
                        "none",
                    ],
                },
            )
        self.send_error(404)

    def do_POST(self):
        body = self._body()
        self.requests.append(("POST", self.path, body, self.headers.get("Authorization")))
        if self.path == "/register":
            type(self).registrations += 1
            number = type(self).registrations
            base = f"http://127.0.0.1:{self.server.server_port}"
            result = {
                "client_id": f"client-{number}",
                "client_secret": f"secret-{number}",
                "client_name": body.get("client_name"),
                "redirect_uris": body.get("redirect_uris"),
                "grant_types": body.get("grant_types"),
                "response_types": body.get("response_types"),
                "token_endpoint_auth_method": body.get("token_endpoint_auth_method"),
            }
            if type(self).include_management:
                result.update(
                    {
                        "registration_client_uri": f"{base}/clients/client-{number}",
                        "registration_access_token": f"registration-token-{number}",
                    }
                )
            return self._send_json(201, result)
        self.send_error(404)

    def do_DELETE(self):
        self.requests.append(("DELETE", self.path, None, self.headers.get("Authorization")))
        if self.path.startswith("/clients/client-"):
            expected = f"Bearer registration-token-{self.path.rsplit('-', 1)[-1]}"
            if self.headers.get("Authorization") != expected:
                return self._send_json(401, {"error": "invalid_token"})
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)


class TestManagedOAuthClient:
    def setup_method(self):
        OAuthHandler.requests = []
        OAuthHandler.registrations = 0
        OAuthHandler.include_management = True
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), OAuthHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def teardown_method(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def metadata_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/metadata"

    def run_helper(self, credentials_file: Path, *extra: str):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "ensure",
                "--metadata-url",
                self.metadata_url,
                "--resource",
                "https://mcp.example.com/mcp",
                "--credentials-file",
                str(credentials_file),
                "--client-name",
                "Heidi reusable MCP client",
                "--redirect-uri",
                "https://claude.ai/api/mcp/auth_callback",
                "--token-endpoint-auth-method",
                "client_secret_post",
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_first_registration_persists_owner_only_credentials_without_printing_secrets(self, tmp_path):
        credentials = tmp_path / "oauth-client.json"
        result = self.run_helper(credentials)

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["action"] == "created"
        assert payload["client_id"] == "client-1"
        assert payload["credentials_file"] == str(credentials)
        assert "secret-1" not in result.stdout
        assert "registration-token-1" not in result.stdout

        stored = json.loads(credentials.read_text(encoding="utf-8"))
        assert stored["client_id"] == "client-1"
        assert stored["client_secret"] == "secret-1"
        assert stored["registration_client_uri"].endswith("/clients/client-1")
        assert stored["registration_access_token"] == "registration-token-1"
        assert stored["resource"] == "https://mcp.example.com/mcp"
        assert stored["redirect_uris"] == ["https://claude.ai/api/mcp/auth_callback"]
        assert stat.S_IMODE(credentials.stat().st_mode) == 0o600

        registration = next(body for method, path, body, _ in OAuthHandler.requests if method == "POST" and path == "/register")
        assert registration == {
            "client_name": "Heidi reusable MCP client",
            "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        }

    def test_matching_registration_is_reused_without_network_reregistration(self, tmp_path):
        credentials = tmp_path / "oauth-client.json"
        first = self.run_helper(credentials)
        assert first.returncode == 0, first.stderr
        requests_after_first = list(OAuthHandler.requests)

        second = self.run_helper(credentials)
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout)["action"] == "reused"
        assert json.loads(second.stdout)["client_id"] == "client-1"
        assert OAuthHandler.requests == requests_after_first
        assert json.loads(credentials.read_text(encoding="utf-8"))["client_secret"] == "secret-1"

    def test_configuration_drift_fails_closed_without_creating_another_client(self, tmp_path):
        credentials = tmp_path / "oauth-client.json"
        first = self.run_helper(credentials)
        assert first.returncode == 0, first.stderr

        changed = self.run_helper(
            credentials,
            "--redirect-uri",
            "https://another.example.com/oauth/callback",
        )
        assert changed.returncode != 0
        assert "configuration" in changed.stderr.lower()
        assert "rotate" in changed.stderr.lower()
        assert OAuthHandler.registrations == 1
        assert json.loads(credentials.read_text(encoding="utf-8"))["client_secret"] == "secret-1"

    def test_explicit_rotation_deletes_old_managed_registration_before_creating_replacement(self, tmp_path):
        credentials = tmp_path / "oauth-client.json"
        first = self.run_helper(credentials)
        assert first.returncode == 0, first.stderr
        OAuthHandler.requests = []

        rotated = self.run_helper(credentials, "--rotate")
        assert rotated.returncode == 0, rotated.stderr
        payload = json.loads(rotated.stdout)
        assert payload["action"] == "rotated"
        assert payload["client_id"] == "client-2"
        assert "secret-2" not in rotated.stdout
        assert json.loads(credentials.read_text(encoding="utf-8"))["client_secret"] == "secret-2"

        mutating = [(method, path) for method, path, _body, _auth in OAuthHandler.requests if method in {"DELETE", "POST"}]
        assert mutating == [("DELETE", "/clients/client-1"), ("POST", "/register")]

    def test_rotation_refuses_when_registration_management_credentials_are_absent(self, tmp_path):
        OAuthHandler.include_management = False
        credentials = tmp_path / "oauth-client.json"
        first = self.run_helper(credentials)
        assert first.returncode == 0, first.stderr
        assert OAuthHandler.registrations == 1

        rotated = self.run_helper(credentials, "--rotate")
        assert rotated.returncode != 0
        assert "registration_client_uri" in rotated.stderr
        assert "registration_access_token" in rotated.stderr
        assert OAuthHandler.registrations == 1
        assert json.loads(credentials.read_text(encoding="utf-8"))["client_secret"] == "secret-1"

    def test_existing_credentials_must_remain_owner_only(self, tmp_path):
        credentials = tmp_path / "oauth-client.json"
        first = self.run_helper(credentials)
        assert first.returncode == 0, first.stderr
        os.chmod(credentials, 0o644)

        reused = self.run_helper(credentials)
        assert reused.returncode != 0
        assert "permission" in reused.stderr.lower()
        assert OAuthHandler.registrations == 1
