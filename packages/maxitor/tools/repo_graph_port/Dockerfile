# packages/maxitor/tools/repo_graph_port/Dockerfile — the repo-graph-port service, built from this repository.
#
# The runtime installs the uv workspace from the repository — no ``aoa-*`` package
# comes from PyPI — with the ``repo-graph-port`` extra only. ``git`` reads the
# repositories; the histories config, the cache and the App's secrets come from
# the environment the container is started with, never from the image.

FROM python:3.12-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /repo
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev --package maxitor --extra repo-graph-port
ENV REPO_GRAPH_PORT_HOST=0.0.0.0
ENV REPO_GRAPH_PORT_PORT=8102
ENV MAXITOR_HISTORY_CACHE=/var/cache/repo-graph-port
ENV PATH="/repo/.venv/bin:$PATH"
EXPOSE 8102
CMD ["repo-graph-port"]
