# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH" \
    FAN_GOVERNANCE_DATA=/app/data/dashboard
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --extra dashboard --no-dev --no-install-project
COPY src/ ./src/
COPY configs/ ./configs/
RUN uv sync --locked --extra dashboard --no-dev \
    && groupadd --gid 10001 dashboard \
    && useradd --uid 10001 --gid dashboard --no-create-home dashboard \
    && mkdir -p /app/data/dashboard \
    && chown -R dashboard:dashboard /app/data
COPY --from=frontend /frontend/dist/ ./frontend/dist/
COPY examples/presentation_studies.py ./examples/presentation_studies.py
USER dashboard
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2).read()"]
CMD ["uvicorn", "fan_governance.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
