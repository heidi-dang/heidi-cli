# ── Stage 1: Build the SvelteKit frontend ──────────────────
FROM --platform=$BUILDPLATFORM node:22-slim AS frontend-builder

WORKDIR /build/frontend
COPY cptr/frontend/package.json cptr/frontend/package-lock.json ./
RUN npm ci
COPY cptr/frontend/ ./
RUN npm run build


# ── Stage 2: Install Python dependencies & build wheel ─────
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-builder

WORKDIR /build
COPY pyproject.toml uv.lock LICENSE README.md CHANGELOG.md ./
COPY cptr/ cptr/

# Drop the pre-built frontend into the package tree
COPY --from=frontend-builder /build/frontend/build cptr/frontend/build

# Build the wheel (includes frontend build as an artifact via hatch)
RUN uv build --wheel --out-dir /dist


# ── Stage 3: Shared runtime ────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/open-webui/computer"
LABEL org.opencontainers.image.description="Open WebUI Computer"

# Direct Coding test profiles execute Node projects at runtime. Reuse the pinned
# Node 22 toolchain from the frontend stage instead of depending on the distro's
# older nodejs/npm packages.
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Runtime deps shared by default and browser images.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gh git tini && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and writable data directory
RUN useradd --create-home --shell /bin/bash cptr && \
    mkdir -p /data && \
    chown -R cptr:cptr /data
USER cptr
WORKDIR /home/cptr

# Install the wheel into an isolated venv
COPY --chown=cptr:cptr --from=backend-builder /dist/*.whl /tmp/
RUN uv venv /home/cptr/.venv && \
    set -- /tmp/*.whl && \
    uv pip install --python /home/cptr/.venv/bin/python "$1[all]" && \
    rm /tmp/*.whl

ENV PATH="/home/cptr/.venv/bin:$PATH"
ENV CPTR_DATA_DIR="/data"

EXPOSE 8000
VOLUME ["/data"]

ENTRYPOINT ["tini", "--"]
CMD ["cptr", "run", "--host", "0.0.0.0", "--port", "8000", "--headless"]


# ── Browser image: Chromium for agent browser automation ───
FROM runtime AS browser

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium && \
    rm -rf /var/lib/apt/lists/*
USER cptr


# ── Default image ──────────────────────────────────────────
# Managed Chrome is part of the supported CPTR control surface, so the default
# production image must be browser-capable as well as the explicit browser tag.
FROM browser AS default
