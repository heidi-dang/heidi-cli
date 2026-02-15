#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python -m pip install -e .

export HEIDI_API_KEY=${HEIDI_API_KEY:-devkey}
export HEIDI_CORS_ORIGINS=${HEIDI_CORS_ORIGINS:-http://localhost:3002}

heidi serve --ui --host 127.0.0.1 --port 7777
