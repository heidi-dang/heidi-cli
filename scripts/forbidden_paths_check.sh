#!/bin/bash
# Forbidden paths check - fails if forbidden paths exist in repo

set -e

echo "Checking for forbidden paths..."

FORBIDDEN=(
    ".venv"
    "venv"
    "__pycache__"
    ".pytest_cache"
    ".ruff_cache"
    ".mypy_cache"
    ".heidi"
    ".git"
)

FOUND=0

for path in "${FORBIDDEN[@]}"; do
    if [ -e "$path" ]; then
        echo "ERROR: Forbidden path found: $path"
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo ""
    echo "ERROR: Forbidden paths detected. Clean before committing."
    exit 1
fi

echo "OK: No forbidden paths found"
exit 0
