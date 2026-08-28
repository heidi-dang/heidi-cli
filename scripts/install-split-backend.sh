#!/usr/bin/env bash
set -euo pipefail
export HEIDI_TOPOLOGY=split-tailscale
export HEIDI_SPLIT_ROLE=backend
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-core.sh" "$@"
