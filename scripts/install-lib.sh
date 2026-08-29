#!/usr/bin/env bash
# Shared Heidi installer primitives. Sourced by install-core.sh only.

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1; }

read_tty() {
  local prompt="$1" default="${2:-}" value
  if [[ "${HEIDI_NONINTERACTIVE:-0}" == 1 ]]; then printf '%s' "$default"; return; fi
  if [[ -n "$default" ]]; then printf '%s [%s]: ' "$prompt" "$default" >"$TTY_DEVICE"; else printf '%s: ' "$prompt" >"$TTY_DEVICE"; fi
  IFS= read -r value <"$TTY_DEVICE" || true
  printf '%s' "${value:-$default}"
}

read_secret() {
  local prompt="$1" value="${2:-}"
  if [[ -n "$value" ]]; then printf '%s' "$value"; return; fi
  [[ "${HEIDI_NONINTERACTIVE:-0}" != 1 ]] || fail "$prompt must be provided through its documented environment variable"
  printf '%s: ' "$prompt" >"$TTY_DEVICE"
  IFS= read -r -s value <"$TTY_DEVICE" || true
  printf '\n' >"$TTY_DEVICE"
  printf '%s' "$value"
}

yes_no() {
  local prompt="$1" default="${2:-y}" raw
  raw="$(read_tty "$prompt (y/n)" "$default")"
  case "${raw,,}" in y|yes) return 0 ;; n|no) return 1 ;; *) fail "please answer y or n: $prompt" ;; esac
}

choose() {
  local prompt="$1" default="$2" allowed="$3" value
  value="$(read_tty "$prompt" "$default")"
  case " $allowed " in *" $value "*) printf '%s' "$value" ;; *) fail "invalid selection '$value' for $prompt; choose one of: $allowed" ;; esac
}

env_line() {
  local key="$1" value="$2"
  value="${value//\\/\\\\}"; value="${value//\"/\\\"}"
  printf '%s="%s"\n' "$key" "$value"
}

sudo_cmd() {
  if [[ "$(id -u)" -eq 0 ]]; then "$@"; else need_cmd sudo || fail "sudo is required for this operation"; sudo "$@"; fi
}

apt_install() {
  need_cmd apt-get || return 1
  sudo_cmd apt-get update -y
  sudo_cmd apt-get install -y --no-install-recommends "$@"
}

ensure_base_dependencies() {
  local missing=() cmd
  for cmd in curl tar git sha256sum openssl python3 cc pkg-config; do need_cmd "$cmd" || missing+=("$cmd"); done
  if ((${#missing[@]})); then
    step "Installing base build dependencies"
    apt_install ca-certificates curl git tar xz-utils openssl python3 python3-venv build-essential pkg-config || fail "cannot automatically install required dependencies: ${missing[*]}"
  fi
  python3 - <<'PY' || fail "Python 3.10+ is required"
import sys
raise SystemExit(0 if sys.version_info >= (3,10) else 1)
PY
  python3 -m venv --help >/dev/null 2>&1 || apt_install python3-venv || fail "python3-venv is required"
}

ensure_host_security_dependencies() {
  local packages=(bubblewrap age)
  need_cmd setcap || packages+=(libcap2-bin)
  if ! need_cmd bwrap || ! need_cmd age || ! need_cmd age-keygen || ! need_cmd setcap; then
    step "Installing sandbox, encryption, and capability dependencies"
    apt_install "${packages[@]}" || fail "bubblewrap, age, and libcap are required for the managed production profile"
  fi
}

manifest_runtime_field() {
  local runtime="$1" platform="$2" field="$3"
  python3 - "$RELEASE_MANIFEST" "$runtime" "$platform" "$field" <<'PY'
import json,sys
m=json.load(open(sys.argv[1],encoding='utf-8'))
v=m.get('runtimes',{}).get(sys.argv[2],{}).get(sys.argv[3],{}).get(sys.argv[4])
if not isinstance(v,str) or not v: raise SystemExit(2)
print(v)
PY
}

platform_key() {
  local arch
  arch="$(uname -m)"
  case "$arch" in x86_64|amd64) printf 'linux-x64' ;; aarch64|arm64) printf 'linux-arm64' ;; *) fail "unsupported Linux architecture: $arch" ;; esac
}

download_verified_runtime() {
  local runtime="$1" destination="$2" platform url sha tmp actual
  platform="$(platform_key)"
  [[ -r "$RELEASE_MANIFEST" ]] || fail "signed release manifest is unavailable; cannot verify runtime $runtime"
  url="$(manifest_runtime_field "$runtime" "$platform" url)" || fail "signed release does not define $runtime for $platform"
  sha="$(manifest_runtime_field "$runtime" "$platform" sha256)" || fail "signed release does not define $runtime checksum for $platform"
  [[ "$sha" =~ ^[0-9a-f]{64}$ ]] || fail "signed $runtime SHA-256 is invalid"
  tmp="$destination.next"
  mkdir -p "$(dirname "$destination")"
  curl -fL --proto '=https' --tlsv1.2 "$url" -o "$tmp"
  actual="$(sha256sum "$tmp" | awk '{print $1}')"
  [[ "$actual" == "$sha" ]] || { rm -f "$tmp"; fail "$runtime checksum mismatch"; }
  chmod 0755 "$tmp"
  mv "$tmp" "$destination"
}

ensure_node() {
  if need_cmd node && need_cmd npm; then
    local major; major="$(node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)"
    if [[ "$major" -ge 22 ]]; then NODE_BIN="$(command -v node)"; NPM_BIN="$(command -v npm)"; return; fi
  fi
  step "Installing signed Node.js runtime"
  local platform archive url sha actual
  platform="$(platform_key)"
  url="$(manifest_runtime_field node "$platform" url)" || fail "signed release lacks Node runtime"
  sha="$(manifest_runtime_field node "$platform" sha256)" || fail "signed release lacks Node checksum"
  archive="$RUNTIME_DIR/node.tar.xz"
  curl -fL --proto '=https' --tlsv1.2 "$url" -o "$archive"
  actual="$(sha256sum "$archive" | awk '{print $1}')"; [[ "$actual" == "$sha" ]] || fail "Node.js checksum mismatch"
  rm -rf "$RUNTIME_DIR/node.next"; mkdir -p "$RUNTIME_DIR/node.next"
  tar -xJf "$archive" -C "$RUNTIME_DIR/node.next" --strip-components=1
  rm -f "$archive"; rm -rf "$RUNTIME_DIR/node"; mv "$RUNTIME_DIR/node.next" "$RUNTIME_DIR/node"
  NODE_BIN="$RUNTIME_DIR/node/bin/node"; NPM_BIN="$RUNTIME_DIR/node/bin/npm"; export PATH="$RUNTIME_DIR/node/bin:$PATH"
}

ensure_rust() {
  if need_cmd cargo && need_cmd rustc; then CARGO_BIN="$(command -v cargo)"; return; fi
  step "Installing signed rustup bootstrap"
  download_verified_runtime rustup "$RUNTIME_DIR/rustup-init"
  "$RUNTIME_DIR/rustup-init" -y --profile minimal --default-toolchain stable --no-modify-path
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
  CARGO_BIN="$(command -v cargo)"
}

ensure_cloudflared() {
  [[ -x "$BIN_DIR/cloudflared" ]] || { step "Installing signed cloudflared runtime"; download_verified_runtime cloudflared "$BIN_DIR/cloudflared"; }
  "$BIN_DIR/cloudflared" --version >/dev/null
}

ensure_caddy() {
  if need_cmd caddy; then CADDY_BIN="$(command -v caddy)"; return; fi
  step "Installing signed Caddy runtime"
  local platform url sha format member archive actual stage
  platform="$(platform_key)"
  url="$(manifest_runtime_field caddy "$platform" url)" || fail "signed release lacks Caddy runtime"
  sha="$(manifest_runtime_field caddy "$platform" sha256)" || fail "signed release lacks Caddy checksum"
  format="$(manifest_runtime_field caddy "$platform" format)" || fail "signed release lacks Caddy format"
  member="$(manifest_runtime_field caddy "$platform" member)" || fail "signed release lacks Caddy archive member"
  [[ "$format" == tar.gz ]] || fail "unsupported signed Caddy artifact format: $format"
  [[ "$member" != */* && "$member" != . && "$member" != .. ]] || fail "unsafe signed Caddy archive member"
  archive="$RUNTIME_DIR/caddy.tar.gz"
  curl -fL --proto '=https' --tlsv1.2 "$url" -o "$archive"
  actual="$(sha256sum "$archive" | awk '{print $1}')"
  [[ "$actual" == "$sha" ]] || { rm -f "$archive"; fail "Caddy checksum mismatch"; }
  stage="$RUNTIME_DIR/caddy.extract.$$"
  rm -rf "$stage"; mkdir -p "$stage"
  tar -xzf "$archive" -C "$stage" "$member"
  [[ -f "$stage/$member" ]] || fail "signed Caddy archive did not contain $member"
  install -m 0755 "$stage/$member" "$BIN_DIR/caddy"
  rm -rf "$stage" "$archive"
  CADDY_BIN="$BIN_DIR/caddy"
  # Binding 80/443 from a user service needs only this narrow file capability.
  sudo_cmd setcap cap_net_bind_service=+ep "$CADDY_BIN"
}

ensure_tailscale() {
  if ! need_cmd tailscale || ! need_cmd tailscaled; then
    step "Installing Tailscale from its signed APT repository"
    [[ -r /etc/os-release ]] || fail "cannot identify Linux distribution for Tailscale installation"
    # shellcheck disable=SC1091
    source /etc/os-release
    local distro="${ID:-}" codename="${VERSION_CODENAME:-}" key_url key_tmp key_sha expected_key_sha list_tmp
    case "$distro" in
      ubuntu|debian) ;;
      *) fail "automatic Tailscale installation currently supports Debian/Ubuntu; install Tailscale first on $distro" ;;
    esac
    [[ -n "$codename" ]] || fail "Linux VERSION_CODENAME is required for the Tailscale package repository"
    expected_key_sha="3e03dacf222698c60b8e2f990b809ca1b3e104de127767864284e6c228f1fb39"
    key_url="https://pkgs.tailscale.com/stable/$distro/$codename.noarmor.gpg"
    key_tmp="$RUNTIME_DIR/tailscale-archive-keyring.gpg.next"
    curl -fL --proto '=https' --tlsv1.2 "$key_url" -o "$key_tmp"
    key_sha="$(sha256sum "$key_tmp" | awk '{print $1}')"
    [[ "$key_sha" == "$expected_key_sha" ]] || fail "Tailscale repository signing-key checksum mismatch"
    sudo_cmd install -d -m 0755 /usr/share/keyrings /etc/apt/sources.list.d
    sudo_cmd install -m 0644 "$key_tmp" /usr/share/keyrings/tailscale-archive-keyring.gpg
    list_tmp="$RUNTIME_DIR/tailscale.list.next"
    printf 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/%s %s main\n' "$distro" "$codename" >"$list_tmp"
    sudo_cmd install -m 0644 "$list_tmp" /etc/apt/sources.list.d/tailscale.list
    apt_install tailscale || fail "Tailscale package installation failed from the official signed repository"
  fi
  sudo_cmd systemctl enable --now tailscaled
  if ! tailscale status >/dev/null 2>&1; then
    local auth_key
    auth_key="$(read_secret 'Tailscale auth key (leave empty for browser login)' "${TAILSCALE_AUTH_KEY:-}")"
    if [[ -n "$auth_key" ]]; then
      sudo_cmd tailscale up --auth-key="$auth_key"
      unset auth_key TAILSCALE_AUTH_KEY || true
    else
      say "Tailscale needs one user authorization. Follow the login URL printed below; Heidi will continue after `tailscale up` succeeds."
      sudo_cmd tailscale up
    fi
  fi
  tailscale status >/dev/null 2>&1 || fail "Tailscale is not connected"
  TAILSCALE_IPV4="$(tailscale ip -4 | head -n1)"
  TAILSCALE_DNS="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName", ""))' || true)"
  [[ -n "$TAILSCALE_IPV4" ]] || fail "Tailscale did not provide an IPv4 address"
}

build_cptr() {
  step "Building CPTR frontend"
  "$NPM_BIN" --prefix "$REPO_DIR/apps/cptr/cptr/frontend" ci
  "$NPM_BIN" --prefix "$REPO_DIR/apps/cptr/cptr/frontend" run build
  step "Installing CPTR Python environment"
  [[ -x "$VENV_DIR/bin/python" ]] || python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  if [[ "$MODE" == development ]]; then "$VENV_DIR/bin/python" -m pip install -e "$REPO_DIR/apps/cptr[all]"; else "$VENV_DIR/bin/python" -m pip install "$REPO_DIR/apps/cptr[all]"; fi
}

build_mcp() {
  step "Building MCP adapter and Live Workbench"
  "$NPM_BIN" --prefix "$REPO_DIR/apps/mcp" ci
  "$NPM_BIN" --prefix "$REPO_DIR/apps/mcp" run build
}

build_fdx() {
  step "Building native FDX"
  "$CARGO_BIN" build --release --manifest-path "$REPO_DIR/Cargo.toml" -p fdx
  install -m 0755 "$REPO_DIR/target/release/fdx" "$BIN_DIR/fdx"
  "$BIN_DIR/fdx" --version
}

bootstrap_cptr_token() {
  local profile="$1"
  CPTR_API_TOKEN="$(CPTR_DATA_DIR="$CPTR_DATA_DIR" "$VENV_DIR/bin/python" "$REPO_DIR/scripts/bootstrap-control-token.py" --username "$(id -un)" --name heidi-mcp --profile "$profile")"
  [[ "$CPTR_API_TOKEN" == sk-cptr-* ]] || fail "scoped CPTR control credential creation failed"
}

random_mcp_token() {
  MCP_ACCESS_TOKEN="$(python3 - <<'PY'
import secrets
print('heidi-mcp-' + secrets.token_urlsafe(32))
PY
)"
}

activate_current_release() {
  local current="$HEIDI_HOME/current" next="$HEIDI_HOME/.current.$$"
  rm -f "$next"; ln -s "$RELEASE_DIR" "$next"; mv -Tf "$next" "$current"
  mkdir -p "$HOME/.local/bin"
  ln -sfn "$HEIDI_HOME/current/source/bin/heidi" "$HOME/.local/bin/heidi"
}

wait_http() {
  local url="$1" label="$2"
  curl -fsS --retry 20 --retry-delay 1 --retry-connrefused --max-time 3 "$url" >/dev/null 2>&1 || fail "$label failed readiness: $url"
}

enable_user_linger() {
  [[ "$MODE" == production ]] || return 0
  need_cmd loginctl || return 0
  if [[ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null || echo no)" != yes ]]; then
    sudo_cmd loginctl enable-linger "$(id -un)" || say "WARNING: systemd user lingering could not be enabled."
  fi
}

select_service_scope() {
  local requested="${HEIDI_SERVICE_SCOPE:-auto}"
  case "$requested" in
    user|system) SERVICE_SCOPE="$requested" ;;
    auto)
      if systemctl --user show-environment >/dev/null 2>&1; then
        SERVICE_SCOPE="user"
      else
        SERVICE_SCOPE="system"
        say "Heidi: systemd user bus is unavailable; using system-scope units with the current user identity."
      fi
      ;;
    *) fail "HEIDI_SERVICE_SCOPE must be auto, user, or system" ;;
  esac
}

systemctl_scope() {
  if [[ "${SERVICE_SCOPE:-user}" == system ]]; then
    sudo_cmd systemctl "$@"
  else
    systemctl --user "$@"
  fi
}

write_service_unit() {
  local unit="$1" content="$2"
  if [[ "${SERVICE_SCOPE:-user}" == system ]]; then
    local staged="$RUNTIME_DIR/$unit"
    printf '%s\n' "$content" >"$staged"
    sudo_cmd install -m 0644 "$staged" "/etc/systemd/system/$unit"
  else
    mkdir -p "$SYSTEMD_DIR"
    printf '%s\n' "$content" >"$SYSTEMD_DIR/$unit"
  fi
}

activate_services() {
  if [[ "${SERVICE_SCOPE:-user}" == user ]]; then enable_user_linger; fi
  systemctl_scope daemon-reload
  local unit
  for unit in $HEIDI_SERVICE_UNITS; do
    systemctl_scope enable --now "$unit"
    systemctl_scope restart "$unit"
  done
}

public_ipv4() {
  curl -fsS --max-time 10 https://api.ipify.org || true
}
