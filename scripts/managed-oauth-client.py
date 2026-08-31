#!/usr/bin/env python3
"""Provision and reuse one confidential OAuth client for Heidi Managed OAuth.

The OAuth client secret and RFC 7592 registration access token are persisted only
in the configured owner-only credential file. Stdout is deliberately redacted so
installer logs can safely consume the lifecycle result.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCHEMA = "heidi.managed-oauth-client.v1"
GRANT_TYPES = ["authorization_code", "refresh_token"]
RESPONSE_TYPES = ["code"]
ALLOWED_AUTH_METHODS = {"client_secret_basic", "client_secret_post"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    ensure = subparsers.add_parser("ensure")
    ensure.add_argument("--metadata-url", required=True)
    ensure.add_argument("--resource", required=True)
    ensure.add_argument("--credentials-file", required=True)
    ensure.add_argument("--client-name", required=True)
    ensure.add_argument("--redirect-uri", action="append", default=[], required=True)
    ensure.add_argument(
        "--token-endpoint-auth-method",
        choices=sorted(ALLOWED_AUTH_METHODS),
        default="client_secret_post",
    )
    ensure.add_argument("--rotate", action="store_true")
    return parser.parse_args()


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_network_url(value: str, label: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.username or parsed.password:
        raise RuntimeError(f"{label} must not contain URL credentials")
    if parsed.fragment:
        raise RuntimeError(f"{label} must not contain a fragment")
    if not parsed.hostname:
        raise RuntimeError(f"{label} must be an absolute URL")
    if parsed.scheme == "https":
        return value
    if parsed.scheme == "http" and _is_loopback_host(parsed.hostname):
        return value
    raise RuntimeError(f"{label} must use HTTPS (loopback HTTP is allowed only for local verification)")


def normalize_redirect_uris(values: list[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        parsed = urllib.parse.urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            raise RuntimeError(f"OAuth redirect URI must be absolute: {value!r}")
        if parsed.fragment:
            raise RuntimeError(f"OAuth redirect URI must not contain a fragment: {value!r}")
        if value not in result:
            result.append(value)
    if not result:
        raise RuntimeError("at least one OAuth redirect URI is required")
    return result


def request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    bearer_token: str | None = None,
    expected_statuses: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    validate_network_url(url, "OAuth endpoint")
    data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": "heidi-managed-oauth-client/2.1"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = int(response.status)
            if status not in expected_statuses:
                raise RuntimeError(f"OAuth {method} request returned unexpected HTTP {status}")
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # Never echo the response body: registration failures can contain
        # implementation-specific data and lifecycle logs must remain secret-free.
        raise RuntimeError(f"OAuth {method} request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OAuth {method} request failed: {exc.reason}") from exc
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OAuth {method} response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"OAuth {method} response must be a JSON object")
    return payload


def delete_registration(url: str, registration_access_token: str) -> None:
    validate_network_url(url, "registration_client_uri")
    req = urllib.request.Request(
        url,
        method="DELETE",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {registration_access_token}",
            "User-Agent": "heidi-managed-oauth-client/2.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if int(response.status) not in (200, 204):
                raise RuntimeError(f"OAuth DELETE request returned unexpected HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OAuth DELETE request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OAuth DELETE request failed: {exc.reason}") from exc


def desired_contract(args: argparse.Namespace, redirect_uris: list[str]) -> dict[str, Any]:
    return {
        "metadata_url": args.metadata_url,
        "resource": args.resource,
        "client_name": args.client_name,
        "redirect_uris": redirect_uris,
        "grant_types": GRANT_TYPES,
        "response_types": RESPONSE_TYPES,
        "token_endpoint_auth_method": args.token_endpoint_auth_method,
    }


def load_credentials(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        raise RuntimeError(f"OAuth credentials file must not be a symlink: {path}")
    if not path.exists():
        return None
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"OAuth credentials path is not a regular file: {path}")
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        raise RuntimeError(
            f"OAuth credentials file permissions are unsafe ({mode:04o}); expected owner-only 0600"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OAuth credentials file is unreadable or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("OAuth credentials file must contain a JSON object")
    if value.get("schema") != SCHEMA:
        raise RuntimeError("OAuth credentials file has an unsupported schema")
    if not str(value.get("client_id") or "").strip() or not str(value.get("client_secret") or "").strip():
        raise RuntimeError("OAuth credentials file is missing client_id or client_secret")
    return value


def contracts_match(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    return all(existing.get(key) == value for key, value in desired.items())


def atomic_write_credentials(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temp_path: Path | None = None
    try:
        fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
        temp_path = Path(raw_path)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def discover_registration(metadata_url: str, auth_method: str) -> tuple[str, str]:
    validate_network_url(metadata_url, "OAuth authorization-server metadata URL")
    metadata = request_json("GET", metadata_url)
    registration_endpoint = str(metadata.get("registration_endpoint") or "").strip()
    if not registration_endpoint:
        raise RuntimeError("OAuth authorization-server metadata does not advertise registration_endpoint")
    validate_network_url(registration_endpoint, "OAuth registration endpoint")
    supported = metadata.get("token_endpoint_auth_methods_supported")
    if isinstance(supported, list) and supported and auth_method not in supported:
        raise RuntimeError(
            f"OAuth authorization server does not advertise token endpoint auth method {auth_method}"
        )
    issuer = str(metadata.get("issuer") or "").strip()
    if not issuer:
        raise RuntimeError("OAuth authorization-server metadata does not advertise issuer")
    validate_network_url(issuer, "OAuth issuer")
    return registration_endpoint, issuer


def register_client(args: argparse.Namespace, redirect_uris: list[str]) -> dict[str, Any]:
    registration_endpoint, issuer = discover_registration(
        args.metadata_url, args.token_endpoint_auth_method
    )
    registration_request = {
        "client_name": args.client_name,
        "redirect_uris": redirect_uris,
        "grant_types": GRANT_TYPES,
        "response_types": RESPONSE_TYPES,
        "token_endpoint_auth_method": args.token_endpoint_auth_method,
        "resource": args.resource,
    }
    registered = request_json(
        "POST",
        registration_endpoint,
        body=registration_request,
        expected_statuses=(200, 201),
    )
    client_id = str(registered.get("client_id") or "").strip()
    client_secret = str(registered.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("OAuth registration did not return both client_id and client_secret")

    stored: dict[str, Any] = {
        "schema": SCHEMA,
        "issuer": issuer,
        "registration_endpoint": registration_endpoint,
        **desired_contract(args, redirect_uris),
        "client_id": client_id,
        "client_secret": client_secret,
    }
    for key in ("registration_client_uri", "registration_access_token"):
        value = str(registered.get(key) or "").strip()
        if value:
            stored[key] = value
    return stored


def redacted_result(action: str, credentials_file: Path, stored: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "client_id": stored["client_id"],
        "credentials_file": str(credentials_file),
        "redirect_uris": stored["redirect_uris"],
    }


def ensure_client(args: argparse.Namespace) -> dict[str, Any]:
    credentials_file = Path(args.credentials_file).expanduser()
    redirect_uris = normalize_redirect_uris(args.redirect_uri)
    desired = desired_contract(args, redirect_uris)
    existing = load_credentials(credentials_file)

    if existing is not None and not args.rotate:
        if not contracts_match(existing, desired):
            raise RuntimeError(
                "existing reusable OAuth client configuration differs from this deployment; "
                "review the redirect/resource settings and rerun with --rotate only when replacement is intended"
            )
        return redacted_result("reused", credentials_file, existing)

    if args.rotate:
        if existing is None:
            raise RuntimeError("cannot rotate reusable OAuth client because no existing credentials file was found")
        registration_client_uri = str(existing.get("registration_client_uri") or "").strip()
        registration_access_token = str(existing.get("registration_access_token") or "").strip()
        if not registration_client_uri or not registration_access_token:
            raise RuntimeError(
                "cannot rotate safely: existing registration is missing registration_client_uri "
                "and/or registration_access_token"
            )
        delete_registration(registration_client_uri, registration_access_token)
        # The remote credential is now revoked. Remove the local stale credential
        # before attempting replacement so a failed registration cannot be reused.
        credentials_file.unlink()
        stored = register_client(args, redirect_uris)
        atomic_write_credentials(credentials_file, stored)
        return redacted_result("rotated", credentials_file, stored)

    stored = register_client(args, redirect_uris)
    atomic_write_credentials(credentials_file, stored)
    return redacted_result("created", credentials_file, stored)


def main() -> int:
    args = parse_args()
    if args.command != "ensure":
        raise RuntimeError(f"unsupported command: {args.command}")
    result = ensure_client(args)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
