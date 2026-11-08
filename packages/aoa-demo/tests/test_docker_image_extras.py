# tests/test_docker_image_extras.py
"""The demo's Docker image installs every extra its model imports (bystrovmaxim/aoa#483)."""

from __future__ import annotations

import re
from pathlib import Path

from aoa.action_machine.resources.postgres import PostgresStorage
from aoa.demo.model.identity.resources.identity_postgres_storage import IdentityPostgresStorage

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _extras() -> set[str]:
    """The extras of the image's ``uv sync``."""
    sync = next(line for line in DOCKERFILE.read_text(encoding="utf-8").splitlines() if line.startswith("RUN uv sync"))
    return set(re.findall(r"--extra (\w+)", sync))


def test_the_image_installs_the_postgres_extra_the_identity_resource_needs() -> None:
    """The identity PostgreSQL store imports the driver, so the model needs the postgres extra."""
    assert issubclass(IdentityPostgresStorage, PostgresStorage)
    assert {"fastapi", "mcp", "postgres"} <= _extras()
