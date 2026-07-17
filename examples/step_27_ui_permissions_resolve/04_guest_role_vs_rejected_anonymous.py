"""
04_guest_role_vs_rejected_anonymous.py — "no token" is not one single outcome

The resolver always calls auth_coordinator.process(request) — but that is not
the same as "requires a real logged-in user". Two genuinely different things
can happen to an unauthenticated request, and this example shows both side by
side so they are never confused:

(a) A coordinator that resolves missing credentials to a real, legitimate
    anonymous Context (the same thing NoAuthCoordinator always does) lets the
    request reach the machine normally. A @check_roles(GuestRole) action then
    gets an honest allowed: true — GuestRole is evaluated exactly like any
    other role, not special-cased inside the resolver.
(b) A coordinator whose process() genuinely returns None (e.g. credentials
    were supplied but are invalid) never reaches the machine at all — the
    resolver answers 403 straight away.

This is the actual FastApiAdapter.build() + TestClient, not just
machine.check_access_decide() directly — the "None vs resolved Context"
distinction lives in the HTTP-layer resolver, not in the machine.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/04_guest_role_vs_rejected_anonymous.py
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class PublicParams(BaseParams):
    pass


class PublicResult(BaseResult):
    message: str = Field(description="Response message")


@meta(description="Browse the public catalog", domain=StoreDomain)
@check_roles(GuestRole)  # open to anyone — declared, not a default
class BrowseCatalogAction(BaseAction[PublicParams, PublicResult]):

    @summary_aspect("Return the catalog")
    async def browse_summary(self, params, state, box, connections):
        return PublicResult(message="catalog")


def _make_client(*, resolved_context: Context | None) -> TestClient:
    machine = ActionProductMachine()
    auth = AsyncMock()
    auth.process.return_value = resolved_context  # simulates one coordinator's decision
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.get("/actions/browse-catalog", BrowseCatalogAction)
    return TestClient(adapter.build())


def main() -> None:
    resolve_body = {"protocol": 1, "items": [{"operation": "BrowseCatalogAction", "params": {}}]}

    # (a) NoAuthCoordinator-style: no credentials, but a real anonymous Context is resolved.
    guest_client = _make_client(resolved_context=Context())
    guest_response = guest_client.post("/permissions/resolve", json=resolve_body)
    print("(a) resolved anonymous Context:")
    print(f"    status = {guest_response.status_code}")
    print(f"    verdict = {guest_response.json()['verdicts'][0]}")

    # (b) A coordinator that genuinely could not authenticate this request.
    rejected_client = _make_client(resolved_context=None)
    rejected_response = rejected_client.post("/permissions/resolve", json=resolve_body)
    print("(b) process() returned None:")
    print(f"    status = {rejected_response.status_code}")  # 403 — AuthorizationError's handler


main()
