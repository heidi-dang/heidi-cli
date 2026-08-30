#!/usr/bin/env bash
set -uo pipefail

CONFIG_DIR="${HEIDI_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/heidi-cli}"
STATE_FILE="$CONFIG_DIR/state.env"
FAIL_CATEGORIES=()
FAIL_LABELS=()
FAIL_DETAILS=()

pass() { printf 'PASS: %s\n' "$*"; }
fail_check() {
  local category="$1" label="$2" detail="${3:-failed}"
  printf 'FAIL: %s — %s\n' "$label" "$detail" >&2
  FAIL_CATEGORIES+=("$category")
  FAIL_LABELS+=("$label")
  FAIL_DETAILS+=("$detail")
}

if [[ ! -f "$STATE_FILE" ]]; then
  printf 'FAIL: Heidi state file is missing: %s\n' "$STATE_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$STATE_FILE"

TOPOLOGY="${HEIDI_TOPOLOGY:-all-in-one}"
ROLE="${HEIDI_SPLIT_ROLE:-all}"
REPO_DIR="${HEIDI_REPO_DIR:-}"
MCP_ENV_FILE="${HEIDI_MCP_ENV_FILE:-$CONFIG_DIR/mcp.env}"

check_tailscale() {
  [[ "$TOPOLOGY" == split-tailscale ]] || return 0
  if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
    pass "Tailscale is connected"
  else
    fail_check tailscale "Tailscale connectivity" "tailscale is missing or not connected to a tailnet"
  fi
}

check_compatibility() {
  local verifier="$REPO_DIR/scripts/verify-compatibility.py"
  if [[ ! -f "$verifier" ]]; then
    fail_check compatibility "Compatibility verifier" "scripts/verify-compatibility.py is missing"
    return
  fi
  if python3 "$verifier" --root "$REPO_DIR" --expected-version "${HEIDI_VERSION:-}" >/dev/null 2>&1; then
    pass "Release compatibility manifest matches canonical component contracts"
  else
    fail_check compatibility "Compatibility manifest" "installed component contract does not match Heidi release ${HEIDI_VERSION:-unknown}"
  fi
}

check_backend() {
  if [[ ! -x "${HEIDI_FDX_BINARY:-}" ]]; then
    fail_check fdx "FDX executable" "${HEIDI_FDX_BINARY:-FDX path missing} is not executable"
  else
    local version
    version="$($HEIDI_FDX_BINARY --version 2>/dev/null || true)"
    if [[ "$version" == fdx* ]]; then pass "FDX executable: $version"; else fail_check fdx "FDX executable" "unexpected version output"; fi
  fi

  if [[ -z "${HEIDI_CPTR_URL:-}" ]]; then
    fail_check cptr_health "CPTR URL" "HEIDI_CPTR_URL is missing"
    return
  fi
  if curl -fsS --max-time 10 "$HEIDI_CPTR_URL/api/health/live" >/dev/null 2>&1; then pass "CPTR liveness"; else fail_check cptr_health "CPTR liveness" "$HEIDI_CPTR_URL/api/health/live is unavailable"; fi
  if curl -fsS --max-time 10 "$HEIDI_CPTR_URL/api/health/ready" >/dev/null 2>&1; then pass "CPTR readiness"; else fail_check cptr_health "CPTR readiness" "$HEIDI_CPTR_URL/api/health/ready is unavailable"; fi
}

read_env_value() {
  local file="$1" key="$2"
  [[ -r "$file" ]] || return 1
  awk -F= -v key="$key" '$1==key {sub(/^[^=]*=/, ""); gsub(/^"|"$/, ""); print; exit}' "$file"
}

check_mcp() {
  if [[ -z "${HEIDI_MCP_LOCAL_URL:-}" ]]; then
    fail_check mcp_health "MCP local URL" "HEIDI_MCP_LOCAL_URL is missing"
    return
  fi
  if curl -fsS --max-time 10 "$HEIDI_MCP_LOCAL_URL/health" >/dev/null 2>&1; then pass "MCP local health"; else fail_check mcp_health "MCP local health" "$HEIDI_MCP_LOCAL_URL/health is unavailable"; return; fi

  local smoke_token node_binary
  smoke_token="$(read_env_value "$MCP_ENV_FILE" MCP_ACCESS_TOKEN 2>/dev/null || true)"
  node_binary="${HEIDI_NODE_BINARY:-$(dirname "$REPO_DIR")/runtime/node/bin/node}"
  if [[ ! -x "$node_binary" ]]; then
    node_binary="$(command -v node 2>/dev/null || true)"
  fi
  if [[ -z "$smoke_token" ]]; then
    fail_check mcp_contract "MCP smoke credential" "MCP_ACCESS_TOKEN cannot be read from the configured environment file"
  elif [[ -z "$node_binary" || ! -x "$node_binary" ]]; then
    fail_check mcp_contract "MCP contract runtime" "Heidi bundled Node runtime is unavailable"
  elif [[ -f "$REPO_DIR/apps/mcp/scripts/check-deployed-contract.mjs" ]]; then
    if CPTR_DEPLOYED_MCP_URL="$HEIDI_MCP_LOCAL_URL/mcp" \
       CPTR_DEPLOYED_MCP_TOKEN="$smoke_token" \
       CPTR_DEPLOYED_PUBLIC_ORIGIN="${HEIDI_PUBLIC_ORIGIN:-$HEIDI_MCP_LOCAL_URL}" \
       "$node_binary" "$REPO_DIR/apps/mcp/scripts/check-deployed-contract.mjs" >/dev/null 2>&1; then
      pass "MCP exact signed tool/resource contract"
    else
      fail_check mcp_contract "MCP exact contract" "registered tools/resources differ from the signed Heidi release"
    fi
  else
    fail_check mcp_contract "MCP contract verifier" "check-deployed-contract.mjs is missing"
  fi

  local cptr_token http_code
  cptr_token="$(read_env_value "$MCP_ENV_FILE" CPTR_API_TOKEN 2>/dev/null || true)"
  if [[ -z "$cptr_token" || -z "${HEIDI_CPTR_URL:-}" ]]; then
    fail_check cptr_auth "MCP→CPTR credential" "private CPTR URL or scoped credential is unavailable"
  else
    http_code="$(curl -sS -o "$CONFIG_DIR/.verify-workspaces.json" -w '%{http_code}' --max-time 10 -H "Authorization: Bearer $cptr_token" "$HEIDI_CPTR_URL/api/control/v1/workspaces" 2>/dev/null || true)"
    if [[ "$http_code" == 200 ]]; then pass "MCP→CPTR authenticated control path"; else fail_check cptr_auth "MCP→CPTR authenticated control path" "HTTP ${http_code:-transport-error}"; fi
    rm -f "$CONFIG_DIR/.verify-workspaces.json"
  fi

  if [[ -n "${HEIDI_PUBLIC_ORIGIN:-}" && "$HEIDI_PUBLIC_ORIGIN" != "$HEIDI_MCP_LOCAL_URL" ]]; then
    local public_code
    public_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$HEIDI_PUBLIC_ORIGIN/health" 2>/dev/null || true)"
    case "$public_code" in
      200|301|302|401|403) pass "Public MCP DNS/TLS/Access edge (HTTP $public_code)" ;;
      *) fail_check cloudflare "Public MCP edge" "HTTP ${public_code:-transport-error} from $HEIDI_PUBLIC_ORIGIN" ;;
    esac
  fi
}

check_sandbox() {
  [[ "$ROLE" == mcp ]] && return 0
  local profile="${HEIDI_SANDBOX_PROFILE:-bubblewrap}"
  case "$profile" in
    bubblewrap)
      if command -v bwrap >/dev/null 2>&1 && bwrap --version >/dev/null 2>&1; then pass "Direct Coding bubblewrap sandbox available"; else fail_check dependency "Direct Coding sandbox" "bubblewrap is selected but bwrap is unavailable"; fi
      ;;
    host) pass "Direct Coding sandbox profile: host (explicit reduced isolation)" ;;
    systemd) command -v systemd-run >/dev/null 2>&1 && pass "Direct Coding systemd-run sandbox available" || fail_check dependency "Direct Coding sandbox" "systemd-run unavailable" ;;
    container) command -v podman >/dev/null 2>&1 && pass "Direct Coding Podman sandbox available" || fail_check dependency "Direct Coding sandbox" "podman unavailable" ;;
    vm) [[ -n "${CPTR_DIRECT_CODING_VM_RUNNER:-}" ]] && pass "Direct Coding VM runner configured" || fail_check dependency "Direct Coding sandbox" "VM runner is not configured" ;;
    *) fail_check compatibility "Direct Coding sandbox" "unsupported profile $profile" ;;
  esac
}

check_tailscale
check_compatibility
case "$TOPOLOGY:$ROLE" in
  split-tailscale:backend) check_backend; check_sandbox ;;
  split-tailscale:mcp) check_mcp ;;
  *) check_backend; check_sandbox; check_mcp ;;
esac

if ((${#FAIL_LABELS[@]})); then
  printf '\nHeidi stack verification: FAILED (%d check%s)\n' "${#FAIL_LABELS[@]}" "$([[ ${#FAIL_LABELS[@]} -eq 1 ]] && echo '' || echo 's')" >&2
  printf '\nAI-assisted repair prompts:\n' >&2
  for i in "${!FAIL_LABELS[@]}"; do
    python3 "$REPO_DIR/scripts/remediation.py" \
      --category "${FAIL_CATEGORIES[$i]}" \
      --failure "${FAIL_LABELS[$i]}: ${FAIL_DETAILS[$i]}" \
      --topology "$TOPOLOGY" --role "$ROLE" >&2 || true
  done
  exit 1
fi

printf '\n============================================================\n'
printf 'Heidi stack verification: PASS\n'
printf 'Release: %s (%s)\n' "${HEIDI_VERSION:-unknown}" "${HEIDI_CHANNEL:-unknown}"
printf 'Topology: %s / %s\n' "$TOPOLOGY" "$ROLE"
if [[ -n "${HEIDI_MCP_URL:-}" ]]; then
  printf 'ChatGPT MCP URL: %s\n' "$HEIDI_MCP_URL"
  printf '\nAdd Heidi to ChatGPT:\n'
  printf '  1. Open ChatGPT Settings → Apps / Connectors (Developer Mode).\n'
  printf '  2. Create or refresh the custom MCP app.\n'
  printf '  3. Enter exactly: %s\n' "$HEIDI_MCP_URL"
  printf '  4. Complete the Cloudflare Access / OAuth authorization when prompted.\n'
  printf '  5. Scan/refresh tools and confirm the Heidi v2.1 contract matches the signed compatibility manifest.\n'
  printf '  6. Start a new chat and run a harmless status/workspace check first.\n'
else
  printf 'This backend role is verified. Use its Split Handoff Report to install the MCP role on the second machine.\n'
fi
printf '============================================================\n'
