# tests/test_docker_image_extras.py
"""The demo's Docker image installs every extra its model imports (bystrovmaxim/aoa#483)."""

from __future__ import annotations

import re
from pathlib import Path

from aoa.action_machine.resources.postgres import PostgresDataSource
from aoa.demo.model.identity.resources.identity_storage import IdentityStorage

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _extras() -> set[str]:
    """The extras of the image's ``uv sync``."""
    sync = next(line for line in DOCKERFILE.read_text(encoding="utf-8").splitlines() if line.startswith("RUN uv sync"))
    return set(re.findall(r"--extra (\w+)", sync))


def test_the_image_installs_the_postgres_extra_the_identity_resource_needs() -> None:
    """``IdentityStorage`` names a PostgreSQL data source: importing the model needs the driver."""
    data_source = IdentityStorage.data_source_type()
    assert data_source is not None and issubclass(data_source, PostgresDataSource)
    assert {"fastapi", "mcp", "postgres"} <= _extras()
