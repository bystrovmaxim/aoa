# tests/adapters/fastapi/test_fastapi_mapper_guards.py
"""
Integration tests: FastAPI adapter rejects mapper outputs that are not the declared types.

``ensure_machine_params`` / ``ensure_protocol_response`` in base_route_record must surface
before or after ``machine.run`` so failures stay at the HTTP boundary (500 via middleware).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from action_machine.integrations.fastapi.adapter import FastApiAdapter
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.domain_model import PingAction, SimpleAction


@pytest.fixture()
def auth() -> AsyncMock:
    a = AsyncMock()
    a.process.return_value = None
    return a


def test_params_mapper_wrong_type_does_not_call_machine_run(
    auth: AsyncMock,
) -> None:
    """params_mapper must return action Params; wrong type → TypeError, run skipped."""
    machine = ActionProductMachine(mode="test")
    machine.run = AsyncMock()

    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post(
        "/mapped",
        SimpleAction,
        params_mapper=lambda _body: PingAction.Params(),  # wrong vs SimpleAction.Params
    )
    app = adapter.build()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/mapped", json={"name": "Alice"})

    assert response.status_code == 500
    machine.run.assert_not_called()
    # Middleware hides exception detail from clients; guard still ran before run.
    assert response.json().get("detail") == "Internal server error"


def test_response_mapper_wrong_type_after_run_returns_500(
    auth: AsyncMock,
) -> None:
    """response_mapper must return effective_response_model type."""
    machine = ActionProductMachine(mode="test")
    machine.run = AsyncMock(
        return_value=SimpleAction.Result(greeting="Hello"),
    )

    class _WireOut(BaseModel):
        greeting: str = Field(default="", description="greeting")

    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post(
        "/out",
        SimpleAction,
        response_model=_WireOut,
        response_mapper=lambda _r: "not-a-model",  # type: ignore[return-value]
    )
    app = adapter.build()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/out", json={"name": "Bob"})

    assert response.status_code == 500
    machine.run.assert_called_once()
    assert response.json().get("detail") == "Internal server error"
