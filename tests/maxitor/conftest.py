# tests/maxitor/conftest.py
"""Shared fixtures for Maxitor package tests."""

from __future__ import annotations

import json
from collections.abc import Iterator
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from aoa.examples.model.services.graph_json_service import ExampleModelGraphJsonService
from aoa.maxitor.api.app import create_app


@pytest.fixture(scope="session", autouse=True)
def _mock_example_model_graph_json_http() -> Iterator[None]:
    """Avoid live HTTP to 127.0.0.1:8001 when :class:`NetworkXGraphResource` is constructed."""
    outer = {"coordinator_json": ExampleModelGraphJsonService().coordinator_json()}

    class _Resp:
        def read(self) -> bytes:
            return json.dumps(outer).encode("utf-8")

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _fake_urlopen(*_args: object, **_kwargs: object) -> _Resp:
        return _Resp()

    with mock.patch(
        "aoa.maxitor.model.core.resources.networkx_graph_resource.urlopen",
        side_effect=_fake_urlopen,
    ):
        yield


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """One FastAPI app + lifespan for the whole pytest session (``build_maxitor_api_session`` is costly)."""
    with TestClient(create_app()) as test_client:
        yield test_client
