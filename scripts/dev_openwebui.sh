#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../openwebui"

# Follow Open WebUI's own dev instructions in its README.
# This script intentionally only positions you in the right folder.
echo "Open WebUI directory contents:"
ls -la
echo ""
echo "See Open WebUI README for dev/build instructions."
