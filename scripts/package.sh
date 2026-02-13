#!/bin/bash
# Clean package script - builds clean source tar/zip excluding forbidden paths

set -e

VERSION=${1:-$(git rev-parse --short HEAD)}
NAME="heidi-cli-${VERSION}"

echo "Building clean package: ${NAME}"

# Create temp directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/${NAME}"

# Copy repo excluding forbidden paths
echo "Copying files..."
rsync -av \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='.mypy_cache' \
    --exclude='.heidi' \
    --exclude='.local' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='*.egg-info' \
    . "${PACKAGE_DIR}/"

# Create tarball
echo "Creating tarball..."
cd "${TEMP_DIR}"
tar -czf "${NAME}.tar.gz" "${NAME}"

# Create zip
echo "Creating zip..."
zip -rq "${NAME}.zip" "${NAME}"

# Move to current directory
mv "${NAME}.tar.gz" "${PWD}/"
mv "${NAME}.zip" "${PWD}/"

# Cleanup
rm -rf "${TEMP_DIR}"

echo ""
echo "Package created:"
echo "  ${NAME}.tar.gz"
echo "  ${NAME}.zip"
