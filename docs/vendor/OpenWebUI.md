# OpenWebUI Vendor Provenance

## Current Version
- **Tag**: v0.8.1
- **Commit**: 883f1dda0f18fbe26aca7aed5a8804021a3685ca
- **Source**: https://github.com/open-webui/open-webui
- **Date**: 2026-02-17

## License
- **License**: MIT (see LICENSE file)
- **Additional**: LICENSE_NOTICE contains attribution notices for third-party components

## Build Notes
- Uses `npm install --legacy-peer-deps` in Dockerfile (peer dependency conflicts in v0.8.1)
- `USE_SLIM=true` build argument skips model preloading for faster builds

## Determinism
- `package-lock.json` is committed - builds should be deterministic
- If CI shows non-deterministic behavior, switch to `npm ci --legacy-peer-deps`

## Local Development
To re-vendor:
```bash
cd /tmp
git clone --depth 1 --branch v0.8.1 https://github.com/open-webui/open-webui upstream-openwebui
# Copy to heidi-cli, force-add any gitignored files
cp -a upstream-openwebli openwebui/
git add -f openwebui/src/lib/ # force-add any gitignored dirs
git commit -m "OpenWebUI: re-vendor v0.8.1"
```
