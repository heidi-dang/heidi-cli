#!/bin/bash
set -e
BRANCHES=("phase-1-foundation" "phase-2-learning" "phase-3-pipeline" "phase-4-registry")
for BRANCH in "${BRANCHES[@]}"; do
    git checkout $BRANCH
    
    ruff check --fix src tests || true
    
    # Check if there are still unfixed errors
    if ruff check src tests | grep -q 'error'; then
        # specifically fix the f-strings without placeholders and e assigned but never used
        if [ -f "src/heidi_cli/model_host/server.py" ]; then
            sed -i 's/except Exception as e:/except Exception:/g' src/heidi_cli/model_host/server.py
        fi
        ruff check --fix src tests || true
    fi

    git add .
    git commit -m "Auto-fix ruff lint errors properly" || true
    git push origin $BRANCH || true
done
git checkout phase-4-registry
