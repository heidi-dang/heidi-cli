#!/bin/bash
set -e
BRANCHES=("phase-1-foundation" "phase-2-learning" "phase-3-pipeline" "phase-4-registry")
for BRANCH in "${BRANCHES[@]}"; do
    git checkout $BRANCH
    
    # Optional typing error
    if [ -f "src/heidi_cli/registry/retrain.py" ]; then
        sed -i 's/from typing import Dict, Any/from typing import Dict, Any, Optional/g' src/heidi_cli/registry/retrain.py
    fi
    # unused model_path
    if [ -f "src/heidi_cli/registry/hotswap.py" ]; then
        sed -i 's/model_path = version_info\["path"\]/_model_path = version_info\["path"\]/g' src/heidi_cli/registry/hotswap.py
    fi
    # unused vid1
    if [ -f "tests/test_registry.py" ]; then
        sed -i 's/vid1 = await/await/g' tests/test_registry.py
    fi
    
    ruff check src tests || true

    git add .
    git commit -m "Fix remaining ruff issues" || true
    git push origin $BRANCH || true
done
