FROM node:22-alpine AS ui-builder

WORKDIR /app/ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/ ./
RUN npm run build -- --base=/ui/

FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ui-builder /app/ui/dist /app/heidi_cli/ui_dist

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 7777

ENV HEIDI_NO_WIZARD=1
ENV HEIDI_UI_DIST=/app/heidi_cli/ui_dist

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7777/health || exit 1

CMD ["heidi", "serve", "--host", "0.0.0.0", "--port", "7777"]
