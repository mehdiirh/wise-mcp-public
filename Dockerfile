FROM ghcr.io/astral-sh/uv:0.11.14 AS uv
FROM python:3.12-slim AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    WISE_HOST=0.0.0.0 WISE_PORT=8000
WORKDIR /app
RUN groupadd --gid 10001 wise && useradd --uid 10001 --gid wise --no-create-home wise
COPY --from=builder /app/.venv /app/.venv
COPY --chown=wise:wise server.py ./
COPY --chown=wise:wise core/ ./core/
COPY --chown=wise:wise services/ ./services/
COPY --chown=wise:wise ui/ ./ui/
USER wise
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"
CMD ["python", "server.py"]
