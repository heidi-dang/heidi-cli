from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cloudflare-provision.py"


class Handler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str, object]] = []

    def log_message(self, *_args):
        return

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else None

    def _send(self, result):
        raw = json.dumps({"success": True, "errors": [], "messages": [], "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        body = self._body()
        self.requests.append(("GET", self.path, body))
        if self.path == "/client/v4/user/tokens/verify":
            return self._send({"status": "active"})
        if self.path.startswith("/client/v4/zones?name=example.com"):
            return self._send([{"id": "zone", "name": "example.com", "account": {"id": "acct"}}])
        if self.path.startswith("/client/v4/zones/zone/dns_records?"):
            return self._send([])
        if self.path == "/client/v4/accounts/acct/access/organizations":
            return self._send({"auth_domain": "team.cloudflareaccess.com"})
        self.send_error(404)

    def do_POST(self):
        body = self._body()
        self.requests.append(("POST", self.path, body))
        if self.path == "/client/v4/accounts/acct/cfd_tunnel":
            return self._send({"id": "tunnel-1", "token": "tunnel-token"})
        if self.path == "/client/v4/zones/zone/dns_records":
            return self._send({"id": "dns-1"})
        if self.path == "/client/v4/accounts/acct/access/apps":
            return self._send(
                {
                    "id": "app-1",
                    "aud": "audience-1",
                    "domain": "mcp.example.com",
                    "oauth_configuration": {"enabled": True},
                }
            )
        if self.path == "/client/v4/accounts/acct/access/apps/app-1/policies":
            return self._send({"id": "policy-1"})
        self.send_error(404)

    def do_PUT(self):
        body = self._body()
        self.requests.append(("PUT", self.path, body))
        if self.path == "/client/v4/accounts/acct/cfd_tunnel/tunnel-1/configurations":
            return self._send({})
        self.send_error(404)


class CloudflareProvisionTests(unittest.TestCase):
    def setUp(self):
        Handler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_provisions_tunnel_dns_managed_oauth_and_email_policy(self):
        env = os.environ.copy()
        env["CLOUDFLARE_API_TOKEN"] = "test-token"
        env["HEIDI_CLOUDFLARE_API_BASE"] = (
            f"http://127.0.0.1:{self.server.server_port}/client/v4"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--account-id",
                "acct",
                "--zone-id",
                "zone",
                "--domain",
                "mcp.example.com",
                "--origin",
                "http://127.0.0.1:8787",
                "--email",
                "owner@example.com",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tunnel_id"], "tunnel-1")
        self.assertEqual(payload["tunnel_token"], "tunnel-token")
        self.assertEqual(payload["access_app_id"], "app-1")
        self.assertEqual(payload["access_audience"], "audience-1")
        self.assertEqual(payload["access_auth_domain"], "team.cloudflareaccess.com")

        by_path = {(method, path): body for method, path, body in Handler.requests}
        tunnel = by_path[("POST", "/client/v4/accounts/acct/cfd_tunnel")]
        self.assertEqual(tunnel, {"name": "heidi-cli-mcp", "config_src": "cloudflare"})
        ingress = by_path[("PUT", "/client/v4/accounts/acct/cfd_tunnel/tunnel-1/configurations")]
        self.assertEqual(ingress["config"]["ingress"][0]["hostname"], "mcp.example.com")
        self.assertEqual(ingress["config"]["ingress"][0]["service"], "http://127.0.0.1:8787")
        app = by_path[("POST", "/client/v4/accounts/acct/access/apps")]
        self.assertEqual(app["type"], "mcp")
        self.assertTrue(app["oauth_configuration"]["enabled"])
        self.assertTrue(app["oauth_configuration"]["dynamic_client_registration"]["enabled"])
        self.assertIn(
            "https://chatgpt.com/connector/oauth/*",
            app["oauth_configuration"]["dynamic_client_registration"]["allowed_uris"],
        )
        policy = by_path[("POST", "/client/v4/accounts/acct/access/apps/app-1/policies")]
        self.assertEqual(policy["decision"], "allow")
        self.assertEqual(policy["include"], [{"email": {"email": "owner@example.com"}}])

    def test_caddy_transport_discovers_zone_and_creates_proxied_origin_dns(self):
        env = os.environ.copy()
        env["CLOUDFLARE_API_TOKEN"] = "test-token"
        env["HEIDI_CLOUDFLARE_API_BASE"] = f"http://127.0.0.1:{self.server.server_port}/client/v4"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--transport",
                "caddy",
                "--domain",
                "mcp.example.com",
                "--origin",
                "http://127.0.0.1:8787",
                "--origin-address",
                "8.8.8.8",
                "--email",
                "owner@example.com",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["account_id"], "acct")
        self.assertEqual(payload["zone_id"], "zone")
        self.assertEqual(payload["transport"], "caddy")
        self.assertEqual(payload["tunnel_id"], "")
        by_path = {(method, path): body for method, path, body in Handler.requests}
        dns = by_path[("POST", "/client/v4/zones/zone/dns_records")]
        self.assertEqual(dns["type"], "A")
        self.assertEqual(dns["content"], "8.8.8.8")
        self.assertTrue(dns["proxied"])
        self.assertFalse(any(path.endswith("/cfd_tunnel") for _, path, _ in Handler.requests))


if __name__ == "__main__":
    unittest.main()
