# tests/examples/model/test_graph_json_service.py
"""Tests for :class:`~aoa.examples.model.services.graph_json_service.ExampleModelGraphJsonService`."""

from __future__ import annotations

import json

from aoa.examples.model.services.graph_json_service import ExampleModelGraphJsonService


def test_coordinator_json_is_valid_interchange() -> None:
    raw = ExampleModelGraphJsonService().coordinator_json()
    assert isinstance(raw, str)
    data = json.loads(raw)
    assert "nodes" in data
    assert "edges" in data


def test_coordinator_json_cache_returns_same_string() -> None:
    svc = ExampleModelGraphJsonService()
    first = svc.coordinator_json()
    second = svc.coordinator_json()
    assert first == second
