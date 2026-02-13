#!/bin/bash
# Secret leak check - fails if secret patterns found in commits

set -e

echo "Checking for secret leaks in staged changes..."

PATTERNS=(
    "ghp_[a-zA-Z0-9]{36}"
    "github_pat_[a-zA-Z0-9_]{22,}"
    "GITHUB_TOKEN="
    "GH_TOKEN="
    "COPILOT_TOKEN="
    "GITEA_TOKEN="
    "gitlab_token="
    "OPENAI_API_KEY="
    "ANTHROPIC_API_KEY="
    "AWS_ACCESS_KEY="
    "AWS_SECRET_KEY="
)

FOUND=0

# Check staged files
for pattern in "${PATTERNS[@]}"; do
    if git diff --cached -E | grep -E "$pattern" > /dev/null 2>&1; then
        echo "ERROR: Secret pattern found in staged changes: $pattern"
        FOUND=1
    fi
done

# Also check untracked files that would be added
for pattern in "${PATTERNS[@]}"; do
    if git diff -E | grep -E "$pattern" > /dev/null 2>&1; then
        echo "ERROR: Secret pattern found in unstaged changes: $pattern"
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo ""
    echo "ERROR: Secret patterns detected. Remove secrets before committing."
    echo "Hint: Use git reset to unstage, then fix and re-stage."
    exit 1
fi

echo "OK: No secret patterns found"
exit 0
