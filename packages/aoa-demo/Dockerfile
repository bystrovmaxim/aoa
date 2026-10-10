# packages/aoa-demo/Dockerfile — the demonstrator service built from this repository.
#
# Installs the uv workspace with the [fastapi] and [mcp] extras and serves the
# declared entry point; no ``aoa-*`` package ever comes from PyPI.

FROM python:3.12-slim AS runtime
WORKDIR /repo
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev --package aoa-demo --extra fastapi --extra mcp
ENV PATH="/repo/.venv/bin:$PATH"
EXPOSE 8100
CMD ["uvicorn", "aoa.demo.fastapi_mcp_services.app_fastapi_service:app", "--host", "0.0.0.0", "--port", "8100"]
