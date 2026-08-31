#!/usr/bin/env bash
set -euo pipefail
umask 077

[[ "$(uname -s)" == Linux ]] || { printf 'ERROR: managed Heidi deployment currently supports Linux.\n' >&2; exit 1; }

HEIDI_HOME="${HEIDI_HOME:-$HOME/.local/share/heidi-cli}"
RELEASE_DIR="${HEIDI_RELEASE_DIR:-$HEIDI_HOME/releases/${HEIDI_VERSION:-dev}}"
REPO_DIR="${HEIDI_REPO_DIR:-$RELEASE_DIR/source}"
CONFIG_DIR="${HEIDI_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/heidi-cli}"
BIN_DIR="$RELEASE_DIR/bin"
VENV_DIR="$RELEASE_DIR/venv"
RUNTIME_DIR="$RELEASE_DIR/runtime"
RELEASE_MANIFEST="$RELEASE_DIR/heidi-release.json"
TTY_DEVICE="${HEIDI_TTY:-/dev/tty}"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
STATE_FILE="$CONFIG_DIR/state.env"
CPTR_ENV_FILE="$CONFIG_DIR/cptr.env"
MCP_ENV_FILE="$CONFIG_DIR/mcp.env"
MCP_OAUTH_CLIENT_FILE="$CONFIG_DIR/oauth-client.json"
CF_ENV_FILE="$CONFIG_DIR/cloudflare.env"
CADDY_FILE="$CONFIG_DIR/Caddyfile"

# shellcheck source=install-lib.sh
source "$REPO_DIR/scripts/install-lib.sh"

[[ -d "$REPO_DIR/apps/mcp" && -d "$REPO_DIR/apps/cptr" && -d "$REPO_DIR/crates/fdx" ]] || fail "invalid Heidi monorepo source: $REPO_DIR"
mkdir -p "$CONFIG_DIR" "$BIN_DIR" "$RUNTIME_DIR" "$SYSTEMD_DIR" "$HEIDI_HOME/releases"
chmod 700 "$CONFIG_DIR" "$HEIDI_HOME" "$RELEASE_DIR" 2>/dev/null || true

state_default() {
  local key="$1" fallback="$2" value=""
  if [[ -f "$STATE_FILE" ]]; then value="$(awk -F= -v key="$key" '$1==key {sub(/^[^=]*=/, ""); gsub(/^"|"$/, ""); print; exit}' "$STATE_FILE")"; fi
  printf '%s' "${value:-$fallback}"
}

HEIDI_VERSION="${HEIDI_VERSION:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["heidi_version"])' "$REPO_DIR/release/compatibility.json")}"
HEIDI_CHANNEL="${HEIDI_CHANNEL:-$(state_default HEIDI_CHANNEL stable)}"

step "Deployment mode and topology"
MODE="${HEIDI_MODE:-$(state_default HEIDI_MODE production)}"
if [[ -n "${HEIDI_DEPLOY_MODE:-}" ]]; then
  case "$HEIDI_DEPLOY_MODE" in
    production|development) MODE="$HEIDI_DEPLOY_MODE" ;;
    dev) MODE=development ;;
    *) fail "HEIDI_DEPLOY_MODE must be production or dev" ;;
  esac
else
  MODE="$(choose 'Deployment mode: development or production' "$MODE" 'development production')"
fi

TOPOLOGY="${HEIDI_TOPOLOGY:-$(state_default HEIDI_TOPOLOGY all-in-one)}"
TOPOLOGY="$(choose 'Deployment topology: all-in-one or split-tailscale' "$TOPOLOGY" 'all-in-one split-tailscale')"

ROLE=all
if [[ "$TOPOLOGY" == split-tailscale ]]; then
  ROLE="${HEIDI_SPLIT_ROLE:-$(state_default HEIDI_SPLIT_ROLE backend)}"
  ROLE="$(choose 'This machine role: backend (CPTR + FDX) or mcp (public MCP server)' "$ROLE" 'backend mcp')"
fi

INCLUDES_BACKEND=0; INCLUDES_MCP=0
case "$TOPOLOGY:$ROLE" in
  all-in-one:all) INCLUDES_BACKEND=1; INCLUDES_MCP=1 ;;
  split-tailscale:backend) INCLUDES_BACKEND=1 ;;
  split-tailscale:mcp) INCLUDES_MCP=1 ;;
  *) fail "unsupported topology/role combination: $TOPOLOGY/$ROLE" ;;
esac

if [[ -n "${HEIDI_CONTROL_PROFILE:-}" ]]; then
  CONTROL_PROFILE="$HEIDI_CONTROL_PROFILE"
else
  CONTROL_PROFILE="$(state_default HEIDI_CONTROL_PROFILE developer)"
  [[ "$CONTROL_PROFILE" != standard ]] || CONTROL_PROFILE=developer
fi
[[ "$CONTROL_PROFILE" != full ]] || CONTROL_PROFILE=owner-full
case "$CONTROL_PROFILE" in
  standard|developer|owner-full) ;;
  *) fail "HEIDI_CONTROL_PROFILE must be standard, developer, or owner-full" ;;
esac
if [[ "$INCLUDES_BACKEND" == 1 && "${HEIDI_NONINTERACTIVE:-0}" != 1 ]]; then
  if yes_no "Enable owner-full control (approved external commands plus confirmed managed-workspace deletion)" "$( [[ "$CONTROL_PROFILE" == owner-full ]] && echo y || echo n )"; then
    CONTROL_PROFILE=owner-full
  elif [[ "$CONTROL_PROFILE" == owner-full ]]; then
    CONTROL_PROFILE=developer
  fi
fi

CPTR_PORT="${HEIDI_CPTR_PORT:-$(state_default HEIDI_CPTR_PORT 8000)}"
MCP_PORT="${HEIDI_MCP_PORT:-$(state_default HEIDI_MCP_PORT 8787)}"
[[ "$INCLUDES_BACKEND" == 0 ]] || CPTR_PORT="$(read_tty 'CPTR port' "$CPTR_PORT")"
[[ "$INCLUDES_MCP" == 0 ]] || MCP_PORT="$(read_tty 'MCP loopback port' "$MCP_PORT")"
[[ "$CPTR_PORT" =~ ^[0-9]+$ && "$MCP_PORT" =~ ^[0-9]+$ ]] || fail "ports must be numeric"
[[ "$CPTR_PORT" != "$MCP_PORT" ]] || fail "CPTR and MCP ports must differ"

ensure_base_dependencies
ensure_node
if [[ "$INCLUDES_BACKEND" == 1 ]]; then
  ensure_host_security_dependencies
  ensure_rust
fi
if [[ "$TOPOLOGY" == split-tailscale ]]; then ensure_tailscale; fi

# Preserve user state before replacing a previously active version.
if [[ "$INCLUDES_BACKEND" == 1 && -f "$STATE_FILE" && -d "${HOME}/.cptr" ]]; then
  step "Creating encrypted pre-upgrade CPTR backup"
  HEIDI_CONFIG_DIR="$CONFIG_DIR" python3 "$REPO_DIR/scripts/lifecycle.py" backup || fail "pre-upgrade encrypted backup failed"
fi

if [[ "$INCLUDES_BACKEND" == 1 ]]; then build_cptr; build_fdx; fi
if [[ "$INCLUDES_MCP" == 1 ]]; then build_mcp; fi

CPTR_DATA_DIR="${HEIDI_CPTR_DATA_DIR:-$(state_default HEIDI_CPTR_DATA_DIR "$HOME/.cptr")}"; mkdir -p "$CPTR_DATA_DIR"; chmod 700 "$CPTR_DATA_DIR" 2>/dev/null || true
CPTR_HOST=127.0.0.1
CPTR_URL=""
CPTR_API_TOKEN=""
if [[ "$INCLUDES_BACKEND" == 1 ]]; then
  [[ "$TOPOLOGY" != split-tailscale ]] || CPTR_HOST="$TAILSCALE_IPV4"
  CPTR_URL="http://$CPTR_HOST:$CPTR_PORT"
  bootstrap_cptr_token "$CONTROL_PROFILE"
fi

# The split MCP role consumes the secure backend handoff generated on machine A.
HANDOFF_FILE=""
if [[ "$TOPOLOGY:$ROLE" == split-tailscale:mcp ]]; then
  step "Backend handoff"
  HANDOFF_FILE="${HEIDI_HANDOFF_FILE:-$(read_tty 'Backend handoff JSON path (leave blank to enter values manually)' '')}"
  if [[ -n "$HANDOFF_FILE" ]]; then
    [[ -r "$HANDOFF_FILE" ]] || fail "handoff file is not readable: $HANDOFF_FILE"
    CPTR_URL="$(python3 "$REPO_DIR/scripts/split-handoff.py" read --input "$HANDOFF_FILE" --field cptr_private_url)"
    CPTR_API_TOKEN="$(python3 "$REPO_DIR/scripts/split-handoff.py" read --input "$HANDOFF_FILE" --field cptr_api_token)"
    HANDOFF_COMPAT="$(python3 "$REPO_DIR/scripts/split-handoff.py" read --input "$HANDOFF_FILE" --field compatibility_version)"
    [[ "$HANDOFF_COMPAT" == "$HEIDI_VERSION" ]] || fail "split handoff is from Heidi $HANDOFF_COMPAT but this server is installing $HEIDI_VERSION"
  else
    CPTR_URL="${HEIDI_CPTR_URL:-$(read_tty 'Backend CPTR private Tailscale URL' '')}"
    CPTR_API_TOKEN="$(read_secret 'Scoped CPTR API token from the backend handoff' "${HEIDI_CPTR_API_TOKEN:-}")"
  fi
  [[ "$CPTR_URL" == http://100.*:* || "$CPTR_URL" == http://*.ts.net:* || "$CPTR_URL" == https://*.ts.net:* ]] || say "WARNING: CPTR URL does not look like a Tailscale address; Heidi will still verify it before public deployment."
  CODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 -H "Authorization: Bearer $CPTR_API_TOKEN" "$CPTR_URL/api/control/v1/workspaces" || true)"
  [[ "$CODE" == 200 ]] || fail "private MCP→CPTR handoff verification failed before public deployment (HTTP ${CODE:-transport-error})"
  pass_msg="Private Tailscale MCP→CPTR control path verified"
  say "$pass_msg"
fi

MCP_LOCAL_URL=""; MCP_URL=""; PUBLIC_ORIGIN=""; PUBLIC_TRANSPORT=none
MCP_DOMAIN=""; MCP_ALLOWED_EMAIL=""; CF_ACCOUNT_ID=""; CF_ZONE_ID=""; CF_TUNNEL_ID=""; CF_ACCESS_APP_ID=""; CF_ACCESS_AUDIENCE=""; CF_ACCESS_AUTH_DOMAIN=""; CF_TUNNEL_TOKEN=""
MCP_OAUTH_CLIENT_ID=""; MCP_OAUTH_CLIENT_STATE_FILE=""
PUBLIC_DEPLOYMENT=0
if [[ "$INCLUDES_MCP" == 1 ]]; then
  MCP_LOCAL_URL="http://127.0.0.1:$MCP_PORT"
  PUBLIC_ORIGIN="$MCP_LOCAL_URL"; MCP_URL="$MCP_LOCAL_URL/mcp"
  if [[ "$MODE" == production ]]; then PUBLIC_DEPLOYMENT=1; elif yes_no "Expose this development MCP publicly for ChatGPT" n; then PUBLIC_DEPLOYMENT=1; fi
fi

if [[ "$PUBLIC_DEPLOYMENT" == 1 ]]; then
  step "Public MCP and automatic Cloudflare configuration"
  PUBLIC_TRANSPORT="${HEIDI_PUBLIC_TRANSPORT:-$(state_default HEIDI_PUBLIC_TRANSPORT caddy)}"
  PUBLIC_TRANSPORT="$(choose 'Public transport: caddy (recommended) or cloudflare-tunnel' "$PUBLIC_TRANSPORT" 'caddy cloudflare-tunnel')"
  MCP_DOMAIN="${HEIDI_MCP_DOMAIN:-$(state_default HEIDI_MCP_DOMAIN '')}"; MCP_DOMAIN="$(read_tty 'Public MCP hostname (for example mcp.example.com)' "$MCP_DOMAIN")"
  MCP_ALLOWED_EMAIL="${HEIDI_MCP_ALLOWED_EMAIL:-$(state_default HEIDI_MCP_ALLOWED_EMAIL '')}"; MCP_ALLOWED_EMAIL="$(read_tty 'Email allowed to authorize the ChatGPT MCP app' "$MCP_ALLOWED_EMAIL")"
  [[ "$MCP_DOMAIN" == *.* && "$MCP_ALLOWED_EMAIL" == *@* ]] || fail "valid public hostname and allowed email are required"
  CF_API_TOKEN="$(read_secret 'Cloudflare API token' "${CLOUDFLARE_API_TOKEN:-}")"; [[ -n "$CF_API_TOKEN" ]] || fail "Cloudflare API token is required"

  CLAUDE_MCP_OAUTH_REDIRECT_URI="https://claude.ai/api/mcp/auth_callback"
  OAUTH_ALLOWED_REDIRECT_URIS=("$CLAUDE_MCP_OAUTH_REDIRECT_URI")
  if [[ -n "${MCP_OAUTH_REDIRECT_URIS:-}" ]]; then
    IFS=',' read -r -a oauth_configured_redirects <<<"$MCP_OAUTH_REDIRECT_URIS"
    for oauth_redirect_uri in "${oauth_configured_redirects[@]}"; do
      oauth_redirect_uri="${oauth_redirect_uri#"${oauth_redirect_uri%%[![:space:]]*}"}"
      oauth_redirect_uri="${oauth_redirect_uri%"${oauth_redirect_uri##*[![:space:]]}"}"
      [[ -n "$oauth_redirect_uri" ]] || continue
      oauth_redirect_seen=0
      for oauth_existing_redirect in "${OAUTH_ALLOWED_REDIRECT_URIS[@]}"; do
        if [[ "$oauth_existing_redirect" == "$oauth_redirect_uri" ]]; then oauth_redirect_seen=1; break; fi
      done
      [[ "$oauth_redirect_seen" == 1 ]] || OAUTH_ALLOWED_REDIRECT_URIS+=("$oauth_redirect_uri")
    done
  fi

  CF_ARGS=(--domain "$MCP_DOMAIN" --origin "$MCP_LOCAL_URL" --email "$MCP_ALLOWED_EMAIL")
  for oauth_redirect_uri in "${OAUTH_ALLOWED_REDIRECT_URIS[@]}"; do
    CF_ARGS+=(--oauth-redirect-uri "$oauth_redirect_uri")
  done
  if [[ "$PUBLIC_TRANSPORT" == caddy ]]; then
    ensure_caddy
    ORIGIN_IP="${HEIDI_PUBLIC_IP:-$(public_ipv4)}"; ORIGIN_IP="$(read_tty 'Public IP of this MCP server' "$ORIGIN_IP")"
    [[ -n "$ORIGIN_IP" ]] || fail "Caddy public transport requires the server public IP"
    CF_ARGS+=(--transport caddy --origin-address "$ORIGIN_IP")
  else
    ensure_cloudflared
    CF_ARGS+=(--transport tunnel)
  fi
  CF_RESULT="$(CLOUDFLARE_API_TOKEN="$CF_API_TOKEN" python3 "$REPO_DIR/scripts/cloudflare-provision.py" "${CF_ARGS[@]}")" || fail "Cloudflare provisioning failed"
  unset CF_API_TOKEN CLOUDFLARE_API_TOKEN || true
  cf_value() { printf '%s' "$CF_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"; }
  CF_ACCOUNT_ID="$(cf_value account_id)"; CF_ZONE_ID="$(cf_value zone_id)"; CF_TUNNEL_ID="$(cf_value tunnel_id)"; CF_TUNNEL_TOKEN="$(cf_value tunnel_token)"
  CF_ACCESS_APP_ID="$(cf_value access_app_id)"; CF_ACCESS_AUDIENCE="$(cf_value access_audience)"; CF_ACCESS_AUTH_DOMAIN="$(cf_value access_auth_domain)"
  [[ -n "$CF_ACCESS_AUDIENCE" && -n "$CF_ACCESS_AUTH_DOMAIN" ]] || fail "Cloudflare Access provisioning returned incomplete OAuth data"
  [[ "$CF_ACCESS_AUTH_DOMAIN" == http*://* ]] || CF_ACCESS_AUTH_DOMAIN="https://$CF_ACCESS_AUTH_DOMAIN"
  PUBLIC_ORIGIN="https://$MCP_DOMAIN"; MCP_URL="$PUBLIC_ORIGIN/mcp"

  GLOBAL_OAUTH_ENABLED="${HEIDI_MCP_OAUTH_GLOBAL_CLIENT:-1}"
  GLOBAL_OAUTH_ROTATE="${HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE:-0}"
  [[ "$GLOBAL_OAUTH_ENABLED" == 0 || "$GLOBAL_OAUTH_ENABLED" == 1 ]] || fail "HEIDI_MCP_OAUTH_GLOBAL_CLIENT must be 0 or 1"
  [[ "$GLOBAL_OAUTH_ROTATE" == 0 || "$GLOBAL_OAUTH_ROTATE" == 1 ]] || fail "HEIDI_MCP_OAUTH_GLOBAL_CLIENT_ROTATE must be 0 or 1"
  [[ "$GLOBAL_OAUTH_ENABLED" == 1 || "$GLOBAL_OAUTH_ROTATE" == 0 ]] || fail "cannot rotate reusable OAuth client while HEIDI_MCP_OAUTH_GLOBAL_CLIENT=0"
  if [[ "$GLOBAL_OAUTH_ENABLED" == 1 ]]; then
    GLOBAL_OAUTH_METADATA_URL="${CF_ACCESS_AUTH_DOMAIN%/}/.well-known/oauth-authorization-server"
    GLOBAL_OAUTH_ARGS=(
      ensure
      --metadata-url "$GLOBAL_OAUTH_METADATA_URL"
      --resource "$PUBLIC_ORIGIN"
      --credentials-file "$MCP_OAUTH_CLIENT_FILE"
      --client-name "${HEIDI_MCP_OAUTH_GLOBAL_CLIENT_NAME:-Heidi reusable MCP client}"
      --token-endpoint-auth-method client_secret_post
    )
    for oauth_redirect_uri in "${OAUTH_ALLOWED_REDIRECT_URIS[@]}"; do
      GLOBAL_OAUTH_ARGS+=(--redirect-uri "$oauth_redirect_uri")
    done
    [[ "$GLOBAL_OAUTH_ROTATE" == 0 ]] || GLOBAL_OAUTH_ARGS+=(--rotate)
    GLOBAL_OAUTH_RESULT="$(python3 "$REPO_DIR/scripts/managed-oauth-client.py" "${GLOBAL_OAUTH_ARGS[@]}")" || fail "reusable Managed OAuth client provisioning failed"
    oauth_client_value() { printf '%s' "$GLOBAL_OAUTH_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"; }
    MCP_OAUTH_CLIENT_ID="$(oauth_client_value client_id)"
    [[ -n "$MCP_OAUTH_CLIENT_ID" ]] || fail "reusable Managed OAuth client provisioning returned no client_id"
    MCP_OAUTH_CLIENT_STATE_FILE="$MCP_OAUTH_CLIENT_FILE"
  fi
fi

random_mcp_token
SANDBOX_PROFILE="${HEIDI_SANDBOX_PROFILE:-bubblewrap}"

step "Writing owner-only configuration"
if [[ "$INCLUDES_BACKEND" == 1 ]]; then
  {
    env_line CPTR_DATA_DIR "$CPTR_DATA_DIR"
    env_line CPTR_FDX_ENABLED true
    env_line CPTR_FDX_BINARY "$HEIDI_HOME/current/bin/fdx"
    env_line CPTR_FDX_REQUEST_TIMEOUT_SECONDS 20
    env_line CPTR_FDX_DAEMON_IDLE_TTL_SECONDS 600
    env_line CPTR_FDX_MAX_DAEMONS 8
    env_line CPTR_DIRECT_CODING_SANDBOX "$SANDBOX_PROFILE"
    env_line PATH "$HEIDI_HOME/current/venv/bin:$HEIDI_HOME/current/runtime/node/bin:$HEIDI_HOME/current/bin:$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
    env_line PYTHONUNBUFFERED 1
  } >"$CPTR_ENV_FILE"; chmod 600 "$CPTR_ENV_FILE"
fi
if [[ "$INCLUDES_MCP" == 1 ]]; then
  {
    env_line NODE_ENV "$( [[ "$MODE" == production ]] && echo production || echo development )"
    env_line HOST 127.0.0.1
    env_line PORT "$MCP_PORT"
    env_line CPTR_BASE_URL "$CPTR_URL"
    env_line CPTR_API_TOKEN "$CPTR_API_TOKEN"
    env_line MCP_ACCESS_TOKEN "$MCP_ACCESS_TOKEN"
    env_line PUBLIC_ORIGIN "$PUBLIC_ORIGIN"
    env_line MCP_ALLOWED_ORIGINS https://chatgpt.com
    env_line MCP_OAUTH_RESOURCE "$MCP_URL"
    env_line CPTR_LIVE_TERMINAL_STREAMING 0
    env_line CPTR_HOT_RELOAD 1
    env_line PATH "$HEIDI_HOME/current/runtime/node/bin:$HEIDI_HOME/current/bin:$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
    if [[ "$PUBLIC_DEPLOYMENT" == 1 ]]; then
      env_line CLOUDFLARE_ACCESS_ISSUER "$CF_ACCESS_AUTH_DOMAIN"
      env_line CLOUDFLARE_ACCESS_AUDIENCE "$CF_ACCESS_AUDIENCE"
      env_line CLOUDFLARE_ACCESS_JWKS_URI "${CF_ACCESS_AUTH_DOMAIN%/}/cdn-cgi/access/certs"
      env_line MCP_OAUTH_ALLOWED_EMAIL "$MCP_ALLOWED_EMAIL"
      env_line MCP_OAUTH_SCOPES ""
    fi
  } >"$MCP_ENV_FILE"; chmod 600 "$MCP_ENV_FILE"
fi
if [[ "$PUBLIC_TRANSPORT" == cloudflare-tunnel ]]; then
  [[ -n "$CF_TUNNEL_TOKEN" ]] || fail "Cloudflare Tunnel provisioning returned no runtime token"
  { env_line TUNNEL_TOKEN "$CF_TUNNEL_TOKEN"; env_line NO_AUTOUPDATE true; env_line TUNNEL_LOGLEVEL info; } >"$CF_ENV_FILE"; chmod 600 "$CF_ENV_FILE"
fi
if [[ "$PUBLIC_TRANSPORT" == caddy ]]; then
  cat >"$CADDY_FILE" <<EOF
{
  admin off
}
$MCP_DOMAIN {
  encode zstd gzip
  reverse_proxy 127.0.0.1:$MCP_PORT
}
EOF
  chmod 600 "$CADDY_FILE"
fi

# Systemd is the recommended production supervisor. Foreground mode is kept for
# developer diagnosis only; Podman/Quadlet remains an advanced MCP-only option
# in the compatibility model because containerising CPTR would impair host control.
SUPERVISOR="${HEIDI_SUPERVISOR:-$(state_default HEIDI_SUPERVISOR systemd)}"
SUPERVISOR="$(choose 'Runtime supervisor: systemd (recommended) or foreground' "$SUPERVISOR" 'systemd foreground')"
[[ "$MODE" != production || "$SUPERVISOR" == systemd ]] || fail "production requires systemd so Heidi can guarantee restart/boot persistence and strict verification"
SERVICE_SCOPE=user
SERVICE_USER="$(id -un)"
SERVICE_GROUP="$(id -gn)"
SERVICE_IDENTITY_DIRECTIVES=""
SERVICE_WANTED_BY=default.target
HEIDI_SERVICE_UNITS=""

if [[ "$SUPERVISOR" == systemd ]]; then
  select_service_scope
  if [[ "$SERVICE_SCOPE" == system ]]; then
    SERVICE_WANTED_BY=multi-user.target
    SERVICE_IDENTITY_DIRECTIVES="User=$SERVICE_USER
Group=$SERVICE_GROUP
Environment=HOME=$HOME"
  fi
  if [[ "$INCLUDES_BACKEND" == 1 ]]; then
    write_service_unit heidi-cptr.service "[Unit]
Description=Heidi CPTR backend
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
$SERVICE_IDENTITY_DIRECTIVES
EnvironmentFile=$CPTR_ENV_FILE
WorkingDirectory=$HEIDI_HOME/current/source/apps/cptr
ExecStart=$HEIDI_HOME/current/venv/bin/cptr run --host $CPTR_HOST --port $CPTR_PORT --headless
Restart=on-failure
RestartSec=3
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=$SERVICE_WANTED_BY"
    HEIDI_SERVICE_UNITS+="heidi-cptr.service "
  fi
  if [[ "$INCLUDES_MCP" == 1 ]]; then
    MCP_EXEC="$NODE_BIN $HEIDI_HOME/current/source/apps/mcp/dist/server/index.js"
    [[ "$MODE" == production ]] || MCP_EXEC="$NODE_BIN $HEIDI_HOME/current/source/apps/mcp/scripts/dev.mjs"
    write_service_unit heidi-mcp.service "[Unit]
Description=Heidi ChatGPT MCP adapter
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
$SERVICE_IDENTITY_DIRECTIVES
EnvironmentFile=$MCP_ENV_FILE
WorkingDirectory=$HEIDI_HOME/current/source/apps/mcp
ExecStart=$MCP_EXEC
Restart=on-failure
RestartSec=3
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=$SERVICE_WANTED_BY"
    HEIDI_SERVICE_UNITS+="heidi-mcp.service "
  fi
  if [[ "$PUBLIC_TRANSPORT" == cloudflare-tunnel ]]; then
    write_service_unit heidi-cloudflared.service "[Unit]
Description=Heidi Cloudflare Tunnel
After=network-online.target heidi-mcp.service
Wants=network-online.target
Requires=heidi-mcp.service

[Service]
Type=simple
$SERVICE_IDENTITY_DIRECTIVES
EnvironmentFile=$CF_ENV_FILE
ExecStart=$HEIDI_HOME/current/bin/cloudflared tunnel --no-autoupdate --loglevel info run
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=$SERVICE_WANTED_BY"
    HEIDI_SERVICE_UNITS+="heidi-cloudflared.service "
  elif [[ "$PUBLIC_TRANSPORT" == caddy ]]; then
    write_service_unit heidi-caddy.service "[Unit]
Description=Heidi Caddy HTTPS origin
After=network-online.target heidi-mcp.service
Wants=network-online.target
Requires=heidi-mcp.service

[Service]
Type=simple
$SERVICE_IDENTITY_DIRECTIVES
ExecStart=$HEIDI_HOME/current/bin/caddy run --config $CADDY_FILE --adapter caddyfile
ExecReload=$HEIDI_HOME/current/bin/caddy reload --config $CADDY_FILE --adapter caddyfile
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=$SERVICE_WANTED_BY"
    HEIDI_SERVICE_UNITS+="heidi-caddy.service "
  fi
fi
HEIDI_SERVICE_UNITS="${HEIDI_SERVICE_UNITS% }"

{
  env_line HEIDI_VERSION "$HEIDI_VERSION"
  env_line HEIDI_CHANNEL "$HEIDI_CHANNEL"
  env_line HEIDI_MODE "$MODE"
  env_line HEIDI_TOPOLOGY "$TOPOLOGY"
  env_line HEIDI_SPLIT_ROLE "$ROLE"
  env_line HEIDI_SUPERVISOR "$SUPERVISOR"
  env_line HEIDI_SERVICE_SCOPE "$SERVICE_SCOPE"
  env_line HEIDI_SERVICE_UNITS "$HEIDI_SERVICE_UNITS"
  env_line HEIDI_HOME "$HEIDI_HOME"
  env_line HEIDI_RELEASE_DIR "$HEIDI_HOME/current"
  env_line HEIDI_REPO_DIR "$HEIDI_HOME/current/source"
  env_line HEIDI_VENV_DIR "$HEIDI_HOME/current/venv"
  env_line HEIDI_FDX_BINARY "$( [[ "$INCLUDES_BACKEND" == 1 ]] && echo "$HEIDI_HOME/current/bin/fdx" || echo '')"
  env_line HEIDI_CPTR_DATA_DIR "$CPTR_DATA_DIR"
  env_line HEIDI_CPTR_PORT "$CPTR_PORT"
  env_line HEIDI_MCP_PORT "$MCP_PORT"
  env_line HEIDI_CPTR_URL "$CPTR_URL"
  env_line HEIDI_MCP_LOCAL_URL "$MCP_LOCAL_URL"
  env_line HEIDI_PUBLIC_ORIGIN "$PUBLIC_ORIGIN"
  env_line HEIDI_MCP_URL "$MCP_URL"
  env_line HEIDI_CONTROL_PROFILE "$CONTROL_PROFILE"
  env_line HEIDI_SANDBOX_PROFILE "$SANDBOX_PROFILE"
  env_line HEIDI_PUBLIC_TRANSPORT "$PUBLIC_TRANSPORT"
  env_line HEIDI_MCP_DOMAIN "$MCP_DOMAIN"
  env_line HEIDI_MCP_ALLOWED_EMAIL "$MCP_ALLOWED_EMAIL"
  env_line HEIDI_CF_ACCOUNT_ID "$CF_ACCOUNT_ID"
  env_line HEIDI_CF_ZONE_ID "$CF_ZONE_ID"
  env_line HEIDI_CF_TUNNEL_ID "$CF_TUNNEL_ID"
  env_line HEIDI_CF_ACCESS_APP_ID "$CF_ACCESS_APP_ID"
  env_line HEIDI_MCP_OAUTH_CLIENT_ID "$MCP_OAUTH_CLIENT_ID"
  env_line HEIDI_MCP_OAUTH_CLIENT_FILE "$MCP_OAUTH_CLIENT_STATE_FILE"
  env_line HEIDI_MCP_ENV_FILE "$MCP_ENV_FILE"
} >"$STATE_FILE"; chmod 600 "$STATE_FILE"

activate_current_release
chmod +x "$HEIDI_HOME/current/source/bin/heidi" "$HEIDI_HOME/current/source/scripts/"*.sh "$HEIDI_HOME/current/source/scripts/"*.py 2>/dev/null || true

if [[ "$SUPERVISOR" == systemd ]]; then
  step "Activating stable systemd services"
  activate_services
  [[ "$INCLUDES_BACKEND" == 0 ]] || wait_http "$CPTR_URL/api/health/ready" "CPTR"
  [[ "$INCLUDES_MCP" == 0 ]] || wait_http "$MCP_LOCAL_URL/health" "MCP"
else
  say "Foreground developer mode selected. Start components manually from $HEIDI_HOME/current/source, then run 'heidi verify'."
  exit 0
fi

step "Strict end-to-end verification"
HEIDI_CONFIG_DIR="$CONFIG_DIR" "$HEIDI_HOME/current/source/scripts/verify-stack.sh"

if [[ "$TOPOLOGY:$ROLE" == split-tailscale:backend ]]; then
  HANDOFF_OUTPUT="${HEIDI_HANDOFF_OUTPUT:-$CONFIG_DIR/heidi-split-handoff.json}"
  python3 "$HEIDI_HOME/current/source/scripts/split-handoff.py" create \
    --output "$HANDOFF_OUTPUT" --hostname "$(hostname)" --tailscale-ipv4 "$TAILSCALE_IPV4" --tailscale-dns "$TAILSCALE_DNS" \
    --cptr-url "$CPTR_URL" --cptr-api-token "$CPTR_API_TOKEN" --cptr-api-revision v1 \
    --fdx-version "$($HEIDI_HOME/current/bin/fdx --version)" --fdx-protocol 2 --compatibility-version "$HEIDI_VERSION"
fi

printf '\nHeidi CLI %s installation completed and verified.\n' "$HEIDI_VERSION"
printf 'Topology: %s / %s\n' "$TOPOLOGY" "$ROLE"
printf 'Supervisor: %s (recommended production default: systemd)\n' "$SUPERVISOR"
[[ -z "$MCP_URL" ]] || printf 'ChatGPT MCP URL: %s\n' "$MCP_URL"
