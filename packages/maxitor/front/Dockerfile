# packages/maxitor/front/Dockerfile — Maxitor built from this repository, client included.
#
# The client is built in its own stage from the sources here, and the runtime
# installs the uv workspace from the repository — no ``aoa-*`` package ever
# comes from PyPI.

FROM node:22-alpine AS client-build
WORKDIR /client
COPY packages/maxitor/front/client/package.json packages/maxitor/front/client/package-lock.json ./
RUN npm ci
COPY packages/maxitor/front/client/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
# The map's layouts: ``sfdp`` runs on the server (spec 040).
RUN apt-get update && apt-get install -y --no-install-recommends graphviz && rm -rf /var/lib/apt/lists/*
WORKDIR /repo
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev --package maxitor --extra front
COPY --from=client-build /client/dist ./packages/maxitor/front/src/maxitor/front/static
ENV MAXITOR_API_HOST=0.0.0.0
ENV MAXITOR_API_PORT=8101
ENV PATH="/repo/.venv/bin:$PATH"
EXPOSE 8101
CMD ["maxitor"]
