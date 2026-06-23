"""
01_service.py — Publish Actions over HTTP with FastApiAdapter

The same Action becomes an HTTP endpoint without changing its code. The adapter
builds a FastAPI app: it validates the request, calls auth_coordinator to build a
Context, runs the Action, and maps the Result back to JSON. OpenAPI is generated
from Params/Result and @meta. AuthorizationError -> 403, ValidationFieldError -> 422.

This example uses FastAPI's in-process TestClient, so it runs without starting a
server. In production you serve the returned app with `uvicorn app:app`.

Tutorial: ../../docs/tutorials/step-13-fastapi_draft.md  ·  topic: FastAPI adapter

Run:
    uv run python examples/step_13_fastapi/01_service.py
"""

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import ApplicationRole, GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


class AdminRole(ApplicationRole):
    name = "admin"
    description = "Administrator"


class GreetParams(BaseParams):
    name: str = Field(description="Person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Greeting message")


# ── Open operation: published as-is ──────────────────────────────────────────
@meta(description="Greet a person", domain=GreetingDomain)
@check_roles(GuestRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Build greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {params.name}!")


# ── Protected operation: anonymous callers are rejected with 403 ─────────────
@meta(description="Admin-only ping", domain=GreetingDomain)
@check_roles(AdminRole)
class AdminPingAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Admin ping")
    async def ping_summary(self, params, state, box, connections):
        return GreetResult(message=f"pong for {params.name}")


# ── External v2 schema differs from the contract — bridged at the adapter ────
class GreetV2Body(BaseModel):
    to: str = Field(description="Recipient (v2 field name)")


class GreetV2Response(BaseModel):
    greeting: str = Field(description="Greeting (v2 field name)")


def build_app():
    machine = ActionProductMachine()
    return (
        FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Greetings API")
        .post("/greet", GreetAction, tags=["greetings"])
        .post("/admin/ping", AdminPingAction, tags=["admin"])
        # v2: external shape (to/greeting) bridged to the operation's Params/Result
        .post(
            "/greet/v2",
            GreetAction,
            request_model=GreetV2Body,
            response_model=GreetV2Response,
            params_mapper=lambda body: GreetParams(name=body.to),
            response_mapper=lambda result: GreetV2Response(greeting=result.message),
            tags=["greetings"],
        )
        .build()
    )


def main() -> None:
    client = TestClient(build_app())

    r = client.get("/health")
    print(f"GET  /health     -> {r.status_code} {r.json()}")

    r = client.post("/greet", json={"name": "Alice"})
    print(f"POST /greet      -> {r.status_code} {r.json()}")

    r = client.post("/admin/ping", json={"name": "Alice"})
    print(f"POST /admin/ping -> {r.status_code} {r.json()}   (anonymous, AdminRole required)")

    r = client.post("/greet/v2", json={"to": "Bob"})
    print(f"POST /greet/v2   -> {r.status_code} {r.json()}   (external schema bridged)")


if __name__ == "__main__":
    main()
