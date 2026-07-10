"""
02_auth_override.py — per-route auth_coordinator override.

Run from repository root:
    uv run python examples/step_13_fastapi/02_auth_override.py

Requires:
    pip install "aoa-action-machine" aoa-fastapi-adapter
"""

from typing import Any

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseResult, ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter


class SystemDomain(BaseDomain):
    name = "system"
    description = "System-level operations"


class PingResult(BaseResult):
    message: str = Field(description="Response message")


@meta(description="Health probe.", domain=SystemDomain)
@check_roles(GuestRole)
class PingAction(BaseAction[ParamsStub, PingResult]):

    @summary_aspect("Return a fixed pong message.")
    async def build_summary(self, params, state, box, connections) -> PingResult:
        _ = (params, state, box, connections)
        return PingResult(message="pong")


class DenyAllCoordinator:
    """
    Stand-in for a real strict coordinator (JWT, API key, ...).

    Always returns ``None`` — the adapter turns that into ``AuthorizationError``
    (HTTP 403). Represents the adapter-wide default in this demo.
    """

    async def process(self, request_data: Any) -> Context | None:
        _ = request_data
        return None


def build_app():
    machine = ActionProductMachine()
    strict_default = DenyAllCoordinator()

    return (
        FastApiAdapter(machine=machine, auth_coordinator=strict_default, title="Auth Override Demo")
        .get("/ping", PingAction, tags=["system"])
        .get(
            "/ping-open",
            PingAction,
            tags=["system"],
            auth_coordinator=NoAuthCoordinator(context=Context()),
        )
        .build()
    )


def main() -> None:
    client = TestClient(build_app())

    protected = client.get("/ping")
    print(f"GET /ping      (adapter default, strict) -> {protected.status_code} {protected.json()}")

    opened = client.get("/ping-open")
    print(f"GET /ping-open (route override, open)     -> {opened.status_code} {opened.json()}")


if __name__ == "__main__":
    main()
