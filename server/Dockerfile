# Matemium Cloud Server — FastAPI
# Suitable for Northflank, Railway, Fly, Render, etc.
#
# ISOLATED BUILD:
#   docker build -t matemium-server -f server/Dockerfile ./server
#   (the ./server context + server/.dockerignore guarantees zero leakage
#    from engine / desktop / website / render outputs)
#
# Run:   docker run -p 8080:8080 -e MATEMIUM_SUPABASE_URL=... matemium-server

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MATEMIUM_ENV=production

WORKDIR /app

# System deps (add more if you need psycopg etc in future)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy package definition + source (order for layer caching)
COPY pyproject.toml ./
COPY matemium_server ./matemium_server

RUN pip install --upgrade pip && \
    pip install .

# Non-root user (recommended for PaaS)
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Northflank (and most PaaS) injects $PORT. Default to 8080 if not present.
# Use shell form so $PORT is expanded.
CMD uvicorn matemium_server.app:app --host 0.0.0.0 --port ${PORT:-8080}
