#!/usr/bin/env python3
"""Provision the Cloudflare edge for a Heidi MCP deployment.

Supports either a remotely managed Cloudflare Tunnel or a Caddy HTTPS origin.
The API token is accepted only through CLOUDFLARE_API_TOKEN and is never stored
or printed. Zone/account IDs are discovered from the hostname when omitted.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = os.environ.get("HEIDI_CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4").rstrip("/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id")
    parser.add_argument("--zone-id")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--origin", required=True, help="MCP origin URL")
    parser.add_argument("--email", required=True)
    parser.add_argument("--transport", choices=["tunnel", "caddy"], default="tunnel")
    parser.add_argument("--origin-address", help="Public IPv4/IPv6 of the Caddy origin")
    parser.add_argument("--tunnel-name")
    parser.add_argument("--tunnel-id")
    parser.add_argument("--access-app-id")
    parser.add_argument(
        "--oauth-redirect-uri",
        action="append",
        default=[],
        help="Exact or wildcard Cloudflare Managed OAuth DCR redirect URI; repeat as needed",
    )
    return parser.parse_args()


def request(method: str, path: str, *, body: dict[str, Any] | None = None) -> Any:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is required")
    data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}", method=method, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "heidi-cli-cloudflare-provisioner/2.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:3000]
        try:
            error_payload = json.loads(raw)
            errors = error_payload.get("errors") or []
            message = "; ".join(str(item.get("message") or item) for item in errors) or raw
        except json.JSONDecodeError:
            message = raw
        raise RuntimeError(
            f"Cloudflare API {method} {path} failed: HTTP {exc.code}: {message}. "
            "Check that the API token has the required Zone DNS, Tunnel (when selected), and Access Apps/Policies permissions."
        ) from exc
    if payload.get("success") is not True:
        errors = payload.get("errors") or []
        message = "; ".join(str(item.get("message") or item) for item in errors) or "unknown error"
        raise RuntimeError(f"Cloudflare API {method} {path} failed: {message}")
    return payload.get("result")


def discover_zone(domain: str) -> tuple[str, str]:
    labels = [part for part in domain.strip(".").split(".") if part]
    if len(labels) < 2:
        raise RuntimeError("public MCP domain is invalid")
    candidates = [".".join(labels[-count:]) for count in range(2, len(labels) + 1)]
    for candidate in candidates:
        query = urllib.parse.urlencode({"name": candidate})
        try:
            zones = request("GET", f"/zones?{query}") or []
        except RuntimeError:
            continue
        if zones:
            zone = zones[0]
            zone_id = str(zone.get("id") or "")
            account_id = str((zone.get("account") or {}).get("id") or "")
            if zone_id and account_id:
                return account_id, zone_id
    raise RuntimeError(
        f"could not discover a Cloudflare zone for {domain}; verify the API token can read the target zone"
    )


def resolve_scope(args: argparse.Namespace) -> tuple[str, str]:
    if args.account_id and args.zone_id:
        return str(args.account_id), str(args.zone_id)
    discovered_account, discovered_zone = discover_zone(args.domain)
    if args.account_id and args.account_id != discovered_account:
        raise RuntimeError("provided Cloudflare account ID does not own the discovered DNS zone")
    if args.zone_id and args.zone_id != discovered_zone:
        raise RuntimeError("provided Cloudflare zone ID does not match the public MCP hostname")
    return args.account_id or discovered_account, args.zone_id or discovered_zone


def dns_upsert(zone_id: str, domain: str, record_type: str, target: str) -> str:
    query = urllib.parse.urlencode({"type": record_type, "name": domain})
    existing = request("GET", f"/zones/{zone_id}/dns_records?{query}") or []
    body = {"type": record_type, "name": domain, "content": target, "proxied": True, "ttl": 1}
    if existing:
        result = request("PUT", f"/zones/{zone_id}/dns_records/{existing[0]['id']}", body=body)
    else:
        result = request("POST", f"/zones/{zone_id}/dns_records", body=body)
    return str(result["id"])


def provision_tunnel(args: argparse.Namespace, account_id: str, zone_id: str) -> tuple[str, str, str]:
    tunnel_id = args.tunnel_id
    if tunnel_id:
        tunnel = request("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}")
        if tunnel.get("deleted_at"):
            raise RuntimeError("configured Cloudflare Tunnel has been deleted")
        token_result = request("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token")
        tunnel_token = str(token_result.get("token") if isinstance(token_result, dict) else token_result)
    else:
        tunnel_name = (args.tunnel_name or os.environ.get("HEIDI_CLOUDFLARE_TUNNEL_NAME") or args.domain).strip()
        tunnel = request(
            "POST", f"/accounts/{account_id}/cfd_tunnel",
            body={"name": tunnel_name, "config_src": "cloudflare"},
        )
        tunnel_id = str(tunnel["id"])
        tunnel_token = str(tunnel.get("token") or "")
        if not tunnel_token:
            token_result = request("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token")
            tunnel_token = str(token_result.get("token") if isinstance(token_result, dict) else token_result)
    request(
        "PUT", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
        body={"config": {"ingress": [
            {"hostname": args.domain, "service": args.origin, "originRequest": {}},
            {"service": "http_status:404"},
        ]}},
    )
    dns_id = dns_upsert(zone_id, args.domain, "CNAME", f"{tunnel_id}.cfargotunnel.com")
    return tunnel_id, tunnel_token, dns_id


def provision_caddy(args: argparse.Namespace, zone_id: str) -> tuple[str, str, str]:
    if not args.origin_address:
        raise RuntimeError("Caddy transport requires --origin-address with this server's public IP")
    try:
        address = ipaddress.ip_address(args.origin_address)
    except ValueError as exc:
        raise RuntimeError("Caddy origin address must be a literal public IPv4 or IPv6 address") from exc
    if address.is_loopback or address.is_unspecified or address.is_link_local or address.is_private:
        raise RuntimeError("Caddy origin address must be a publicly routable IP address")
    record_type = "A" if address.version == 4 else "AAAA"
    dns_id = dns_upsert(zone_id, args.domain, record_type, str(address))
    return "", "", dns_id


def configured_oauth_redirect_uris(args: argparse.Namespace) -> list[str]:
    env_values = [
        value.strip()
        for value in os.environ.get("MCP_OAUTH_REDIRECT_URIS", "").split(",")
        if value.strip()
    ]
    cli_values = [str(value).strip() for value in (args.oauth_redirect_uri or []) if str(value).strip()]
    return list(dict.fromkeys([*env_values, *cli_values]))


def existing_oauth_redirect_uris(existing: dict[str, Any] | None) -> list[str]:
    oauth = (existing or {}).get("oauth_configuration") or {}
    dcr = oauth.get("dynamic_client_registration") or {}
    values = dcr.get("allowed_uris") or []
    return [str(value).strip() for value in values if str(value).strip()]


def managed_oauth_configuration(args: argparse.Namespace, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    redirect_uris = list(dict.fromkeys([
        *existing_oauth_redirect_uris(existing),
        *configured_oauth_redirect_uris(args),
    ]))
    return {
        "enabled": True,
        "dynamic_client_registration": {
            "enabled": bool(redirect_uris),
            "allow_any_on_localhost": False,
            "allow_any_on_loopback": False,
            "allowed_uris": redirect_uris,
        },
        "grant": {"access_token_lifetime": "15m", "session_duration": "168h"},
    }


def access_application_body(args: argparse.Namespace, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    current = existing or {}
    return {
        "name": str(current.get("name") or os.environ.get("HEIDI_CLOUDFLARE_ACCESS_APP_NAME") or args.domain),
        "domain": args.domain,
        "type": "mcp",
        "session_duration": str(current.get("session_duration") or os.environ.get("HEIDI_CLOUDFLARE_ACCESS_SESSION_DURATION") or "24h"),
        "app_launcher_visible": bool(current.get("app_launcher_visible", False)),
        "oauth_configuration": managed_oauth_configuration(args, existing),
    }


def provision_access(args: argparse.Namespace, account_id: str) -> tuple[str, str, str]:
    access_app_id = args.access_app_id
    audience = ""
    if access_app_id:
        access_app = request("GET", f"/accounts/{account_id}/access/apps/{access_app_id}")
        if str(access_app.get("domain") or "").rstrip("/") != args.domain.rstrip("/"):
            raise RuntimeError("configured Cloudflare Access application protects a different domain")
        access_app = request(
            "PUT", f"/accounts/{account_id}/access/apps/{access_app_id}",
            body=access_application_body(args, access_app),
        )
        audience = str(access_app.get("aud") or "")
    else:
        access_app = request(
            "POST", f"/accounts/{account_id}/access/apps",
            body=access_application_body(args),
        )
        access_app_id = str(access_app["id"])
        audience = str(access_app.get("aud") or "")
        request(
            "POST", f"/accounts/{account_id}/access/apps/{access_app_id}/policies",
            body={
                "name": os.environ.get("HEIDI_CLOUDFLARE_ACCESS_POLICY_NAME") or "Allow MCP user",
                "decision": "allow",
                "precedence": 1,
                "include": [{"email": {"email": args.email}}],
            },
        )
    if not audience:
        raise RuntimeError("Cloudflare Access application did not return an audience tag")
    organization = request("GET", f"/accounts/{account_id}/access/organizations")
    auth_domain = str(organization.get("auth_domain") or "").strip()
    if not auth_domain:
        raise RuntimeError("Cloudflare Zero Trust organization did not return auth_domain")
    return str(access_app_id), audience, auth_domain


def main() -> int:
    args = parse_args()
    request("GET", "/user/tokens/verify")
    account_id, zone_id = resolve_scope(args)

    if args.transport == "tunnel":
        tunnel_id, tunnel_token, dns_id = provision_tunnel(args, account_id, zone_id)
    else:
        if args.tunnel_id:
            raise RuntimeError("--tunnel-id cannot be used with Caddy transport")
        tunnel_id, tunnel_token, dns_id = provision_caddy(args, zone_id)

    access_app_id, audience, auth_domain = provision_access(args, account_id)
    print(json.dumps({
        "transport": args.transport,
        "account_id": account_id,
        "zone_id": zone_id,
        "tunnel_id": tunnel_id,
        "tunnel_token": tunnel_token,
        "dns_record_id": dns_id,
        "access_app_id": access_app_id,
        "access_audience": audience,
        "access_auth_domain": auth_domain,
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
