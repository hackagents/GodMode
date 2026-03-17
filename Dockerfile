# ---- Stage 1: Build React frontend ----
# To build the frontend inside Docker (e.g. in CI with npm access), uncomment:
# FROM node:20-slim AS frontend
# WORKDIR /app/frontend
# COPY frontend/package.json frontend/package-lock.json ./
# RUN npm ci
# COPY frontend/ ./
# RUN npm run build

# ---- Python runtime ----
FROM python:3.11-slim

# System deps for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend source
COPY story_engine/ story_engine/

# Copy pre-built frontend (run: cd frontend && npm install && npm run build)
# If using the multi-stage build above, replace this with:
# COPY --from=frontend /app/frontend/dist frontend/dist
COPY frontend/dist frontend/dist

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

CMD uv run uvicorn story_engine.main:app --host 0.0.0.0 --port ${PORT}
