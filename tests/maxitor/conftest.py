# tests/maxitor/conftest.py
"""Shared fixtures for Maxitor package tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from aoa.maxitor.api.app import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """One FastAPI app + lifespan for the whole pytest session (``build_maxitor_api_session`` is costly)."""
    with TestClient(create_app()) as test_client:
        yield test_client
