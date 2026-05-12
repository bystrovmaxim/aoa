# tests/examples/model/test_get_example_model_graph_json_action.py
"""Tests for :class:`~aoa.examples.model.actions.get_example_model_graph_json_action.GetExampleModelGraphJsonAction`."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from aoa.action_machine.context.context import Context
from aoa.examples.fastapi_mcp_services.app_fastapi_service import app as examples_app
from aoa.examples.fastapi_mcp_services.infrastructure import machine
from aoa.examples.model.actions import GetExampleModelGraphJsonAction


@pytest.mark.asyncio
async def test_action_run_returns_coordinator_json() -> None:
    action = GetExampleModelGraphJsonAction()
    result = await machine.run(
        Context(),
        action,
        GetExampleModelGraphJsonAction.Params(),
        {},
    )
    assert isinstance(result.coordinator_json, str)
    data = json.loads(result.coordinator_json)
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_fastapi_get_examples_model_graph_json() -> None:
    with TestClient(examples_app) as client:
        response = client.get("/examples/model/graph-json")
    assert response.status_code == 200
    body = response.json()
    assert "coordinator_json" in body
    inner = json.loads(body["coordinator_json"])
    assert "nodes" in inner and "edges" in inner
