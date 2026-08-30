#!/usr/bin/env sh
set -eu

# Heidi's curl bootstrap is deliberately small: it establishes a pinned Ed25519
# trust root, downloads a signed release manifest, verifies the source archive,
# stages that immutable release, and only then transfers control to install-core.
REPO="${HEIDI_GITHUB_REPO:-heidi-dang/heidi-cli}"
CHANNEL="${HEIDI_CHANNEL:-stable}"
VERSION="${HEIDI_VERSION:-}"
HEIDI_HOME="${HEIDI_HOME:-$HOME/.local/share/heidi-cli}"
TTY_DEVICE="${HEIDI_TTY:-/dev/tty}"
TMP_DIR="$HEIDI_HOME/.bootstrap-$$"

say() { printf '%s\n' "$*"; }
fail() { say "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1; }

install_bootstrap_deps() {
  missing=""
  for cmd in curl tar openssl sha256sum python3; do
    need "$cmd" || missing="$missing $cmd"
  done
  [ -z "$missing" ] && return 0
  need apt-get || fail "missing bootstrap dependencies:$missing; automatic apt installation is unavailable"
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
  else
    need sudo || fail "missing bootstrap dependencies:$missing and sudo is unavailable"
    SUDO="sudo"
  fi
  $SUDO apt-get update -y
  $SUDO apt-get install -y --no-install-recommends ca-certificates curl openssl tar xz-utils python3
}

case "$CHANNEL" in stable|beta|edge) ;; *) fail "HEIDI_CHANNEL must be stable, beta, or edge" ;; esac
install_bootstrap_deps
mkdir -p "$HEIDI_HOME" "$TMP_DIR"
chmod 700 "$HEIDI_HOME" 2>/dev/null || true
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

# Embedded trust root. Do not replace this with a key downloaded from the same
# mutable endpoint as the manifest; that would defeat release authentication.
cat >"$TMP_DIR/signing-public.pem" <<'EOF'
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAx33EdK05OwYF68bUH6M+b+rm7OYskdyqe92V9Lh+pJM=
-----END PUBLIC KEY-----
EOF

if [ -n "$VERSION" ]; then
  RELEASE_BASE="${HEIDI_RELEASE_BASE_URL:-https://github.com/$REPO/releases/download/v$VERSION}"
else
  case "$CHANNEL" in
    stable) RELEASE_BASE="${HEIDI_RELEASE_BASE_URL:-https://github.com/$REPO/releases/download/channel-stable}" ;;
    beta) RELEASE_BASE="${HEIDI_RELEASE_BASE_URL:-https://github.com/$REPO/releases/download/channel-beta}" ;;
    edge) RELEASE_BASE="${HEIDI_RELEASE_BASE_URL:-https://github.com/$REPO/releases/download/channel-edge}" ;;
  esac
fi

MANIFEST="$TMP_DIR/heidi-release.json"
SIGNATURE="$TMP_DIR/heidi-release.json.sig"
say "Heidi CLI: fetching signed $CHANNEL release metadata"
curl -fL --proto '=https' --tlsv1.2 "$RELEASE_BASE/heidi-release.json" -o "$MANIFEST"
curl -fL --proto '=https' --tlsv1.2 "$RELEASE_BASE/heidi-release.json.sig" -o "$SIGNATURE"
openssl pkeyutl -verify -pubin -inkey "$TMP_DIR/signing-public.pem" -rawin \
  -in "$MANIFEST" -sigfile "$SIGNATURE" >/dev/null 2>&1 || fail "Heidi release manifest signature verification failed"

manifest_value() {
  python3 - "$MANIFEST" "$1" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
for part in sys.argv[2].split('.'):
    if not isinstance(value, dict) or part not in value:
        raise SystemExit(2)
    value = value[part]
if isinstance(value, (dict, list)):
    print(json.dumps(value, separators=(",", ":")))
else:
    print(value)
PY
}

SIGNED_VERSION="$(manifest_value version)" || fail "signed manifest is missing version"
SIGNED_CHANNEL="$(manifest_value channel)" || fail "signed manifest is missing channel"
SOURCE_URL="$(manifest_value source.url)" || fail "signed manifest is missing source URL"
SOURCE_SHA="$(manifest_value source.sha256)" || fail "signed manifest is missing source SHA-256"
COMPAT_SHA="$(manifest_value compatibility_sha256)" || fail "signed manifest is missing compatibility SHA-256"
[ "$SIGNED_CHANNEL" = "$CHANNEL" ] || { [ -n "$VERSION" ] || fail "release channel mismatch: requested $CHANNEL, signed $SIGNED_CHANNEL"; }
[ -z "$VERSION" ] || [ "$SIGNED_VERSION" = "$VERSION" ] || fail "release version mismatch: requested $VERSION, signed $SIGNED_VERSION"
printf '%s' "$SOURCE_SHA" | grep -Eq '^[0-9a-f]{64}$' || fail "invalid signed source SHA-256"
printf '%s' "$COMPAT_SHA" | grep -Eq '^[0-9a-f]{64}$' || fail "invalid signed compatibility SHA-256"

ARCHIVE="$TMP_DIR/heidi-source.tar.gz"
say "Heidi CLI: downloading verified source v$SIGNED_VERSION"
curl -fL --proto '=https' --tlsv1.2 "$SOURCE_URL" -o "$ARCHIVE"
printf '%s  %s\n' "$SOURCE_SHA" "$ARCHIVE" | sha256sum -c - >/dev/null || fail "Heidi source archive checksum mismatch"

RELEASE_DIR="$HEIDI_HOME/releases/$SIGNED_VERSION"
STAGE="$HEIDI_HOME/releases/.${SIGNED_VERSION}.stage.$$"
mkdir -p "$STAGE/source"
tar -xzf "$ARCHIVE" -C "$STAGE/source" --strip-components=1
[ -f "$STAGE/source/release/compatibility.json" ] || fail "release archive is missing compatibility manifest"
ACTUAL_COMPAT="$(sha256sum "$STAGE/source/release/compatibility.json" | awk '{print $1}')"
[ "$ACTUAL_COMPAT" = "$COMPAT_SHA" ] || fail "compatibility manifest checksum mismatch"
[ -x "$STAGE/source/scripts/install-core.sh" ] || chmod +x "$STAGE/source/scripts/install-core.sh"

# A release is immutable once installed. If the exact version already exists,
# reuse it only when every signed source file still matches the freshly
# downloaded, signature-verified source archive. Extra generated build files are
# ignored because they are not part of the signed source payload.
verify_existing_signed_source() {
  python3 - "$1" "$2" <<'PY'
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

expected = Path(sys.argv[1]).resolve()
installed_arg = Path(sys.argv[2])
if installed_arg.is_symlink():
    raise SystemExit("installed source directory must not be a symlink")
installed = installed_arg.resolve()
if not installed.is_dir():
    raise SystemExit("installed source directory is missing")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

for source in expected.rglob("*"):
    relative = source.relative_to(expected)
    target = installed / relative
    if source.is_symlink():
        if not target.is_symlink() or os.readlink(target) != os.readlink(source):
            raise SystemExit(f"signed source mismatch: {relative}")
        continue
    if source.is_dir():
        if target.is_symlink() or not target.is_dir():
            raise SystemExit(f"signed source directory missing or unsafe: {relative}")
        continue
    if not target.is_file() or target.is_symlink():
        raise SystemExit(f"signed source file missing: {relative}")
    if source.stat().st_size != target.stat().st_size or digest(source) != digest(target):
        raise SystemExit(f"signed source mismatch: {relative}")
PY
}

if [ -e "$RELEASE_DIR" ]; then
  EXISTING_COMPAT="$(sha256sum "$RELEASE_DIR/source/release/compatibility.json" 2>/dev/null | awk '{print $1}' || true)"
  [ "$EXISTING_COMPAT" = "$COMPAT_SHA" ] || fail "installed release v$SIGNED_VERSION differs from the signed release; refusing overwrite"
  verify_existing_signed_source "$STAGE/source" "$RELEASE_DIR/source" || fail "installed release v$SIGNED_VERSION has modified signed source files"
  rm -rf "$STAGE"
else
  mv "$STAGE" "$RELEASE_DIR"
fi

cp "$MANIFEST" "$RELEASE_DIR/heidi-release.json"
cp "$SIGNATURE" "$RELEASE_DIR/heidi-release.json.sig"
chmod 600 "$RELEASE_DIR/heidi-release.json" "$RELEASE_DIR/heidi-release.json.sig" 2>/dev/null || true

export HEIDI_HOME
export HEIDI_RELEASE_DIR="$RELEASE_DIR"
export HEIDI_REPO_DIR="$RELEASE_DIR/source"
export HEIDI_VERSION="$SIGNED_VERSION"
export HEIDI_CHANNEL="$SIGNED_CHANNEL"
export HEIDI_TTY="$TTY_DEVICE"
trap - EXIT INT TERM
exec bash "$RELEASE_DIR/source/scripts/install-core.sh" "$@"
