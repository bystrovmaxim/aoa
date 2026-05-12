# tests/examples/model/conftest.py
"""Fixtures for example model tests."""

from __future__ import annotations

import pytest

from aoa.examples.model.services.graph_json_service import ExampleModelGraphJsonService


@pytest.fixture(autouse=True)
def _clear_example_graph_json_cache() -> None:
    ExampleModelGraphJsonService.clear_cache()
    yield
    ExampleModelGraphJsonService.clear_cache()
