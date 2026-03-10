#!/bin/bash
set -e
BRANCHES=("phase-1-foundation" "phase-2-learning" "phase-3-pipeline" "phase-4-registry")
for BRANCH in "${BRANCHES[@]}"; do
    git checkout $BRANCH
    
    # We will remove the "Build and Start heidid (Linux)" block (13 lines)
    # and the "Stop heidid" block (6 lines) via awk or perl.
    perl -0777 -pi -e 's/      - name: Build and Start heidid.*?sleep 2 # wait for socket\n//s' .github/workflows/ci.yml
    perl -0777 -pi -e 's/      - name: Stop heidid.*?fi\n//s' .github/workflows/ci.yml
    
    git add .
    git commit -m "Fix CI: Remove obsolete heidid build dependency from tests" || true
    git push origin $BRANCH || true
done
git checkout phase-4-registry
