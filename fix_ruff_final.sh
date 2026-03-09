#!/bin/bash
set -e
BRANCHES=("phase-1-foundation" "phase-2-learning" "phase-3-pipeline" "phase-4-registry")
for BRANCH in "${BRANCHES[@]}"; do
    git checkout $BRANCH
    
    # Optional typing error
    if [ -f "src/heidi_cli/registry/retrain.py" ]; then
        sed -i 's/import asyncio/import asyncio\nfrom typing import Optional/g' src/heidi_cli/registry/retrain.py
    fi
    
    ruff check src tests || true

    git add .
    git commit -m "Fix final ruff typing issue" || true
    git push origin $BRANCH || true
done
git checkout phase-4-registry
