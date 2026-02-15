#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ui"

npm ci
npm run dev -- --host 127.0.0.1 --port 3002 --strictPort
