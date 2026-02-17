# Heidi CLI Docker

This document describes how to run Heidi CLI in Docker.

## Quick Start

```bash
# Build the image
docker build -t heididang/heidi-cli:latest .

# Run the container
docker run -d -p 7777:7777 --name heidi-cli heididang/heidi-cli:latest

# Check health
curl http://localhost:7777/health
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HEIDI_NO_WIZARD` | Skip setup wizard | Not set |
| `HEIDI_UI_DIST` | Path to UI dist files | `/app/heidi_cli/ui_dist` |
| `HEIDI_API_KEY` | API key for protected endpoints | Not set |
| `HEIDI_CORS_ORIGINS` | Comma-separated CORS origins | localhost UIs |

## Ports

- `7777` - Heidi CLI server

## Building with UI

To include the built UI, add Node.js and build the UI during the image build:

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -e .

# Build UI
RUN cd ui && npm ci && npm run build -- --base=/ui/
RUN mkdir -p /app/heidi_cli/ui_dist && cp -r ui/dist/* /app/heidi_cli/ui_dist/

EXPOSE 7777

ENV HEIDI_NO_WIZARD=1
ENV HEIDI_UI_DIST=/app/heidi_cli/ui_dist

CMD ["heidi", "serve", "--host", "0.0.0.0", "--port", "7777"]
```

## Security

- Runs as root by default
- No secrets baked into the image
- Use `HEIDI_API_KEY` for API authentication in production

## GitHub Actions (Optional)

To build and push automatically:

```yaml
name: docker-heidi-cli

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          push: true
          tags: heididang/heidi-cli:latest,heididang/heidi-cli:${{ github.ref_name }}
```

Requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets.
