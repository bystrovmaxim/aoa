"""
04_guest_gets_the_same_manifest.py — the catalog is role-independent

GET /client-manifest.json is a pure projection of the adapter's registered
routes: no Context, no role filtering. So the manifest a guest fetches
(NoAuthCoordinator, no token) is byte-for-byte the manifest a logged-in manager
fetches — same manifest_version, same endpoints, in the same order. Even the
manager-only action shows up in the guest's catalog: the manifest lists what
EXISTS, not what this caller may call. Per-role allow/deny is the resolver's
job (POST /permissions/resolve), never the manifest's.

The only fork is "did auth pass at all", not "which role". A coordinator whose
process() returns None (bad credentials) gets 403 before any projection runs; a
resolved anonymous Context (NoAuthCoordinator) sails straight through.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/04_guest_gets_the_same_manifest.py
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
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


class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)  # manager-only — still listed in every caller's catalog
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


class PublicParams(BaseParams):
    pass


class PublicResult(BaseResult):
    message: str = Field(description="Response message")


@meta(description="Browse the public catalog", domain=StoreDomain)
@check_roles(GuestRole)  # open to anyone
class BrowseCatalogAction(BaseAction[PublicParams, PublicResult]):

    @summary_aspect("Return the catalog")
    async def browse_summary(self, params, state, box, connections):
        return PublicResult(message="catalog")


def _client_with(auth_coordinator) -> TestClient:
    """Build the SAME two-route adapter, varying only the auth coordinator.

    The manifest is a projection of these two routes — nothing about the
    coordinator or the caller's roles feeds into it — so any two clients built
    here produce identical manifest bodies.
    """
    machine = ActionProductMachine(loggers=[])
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth_coordinator)
    adapter.post("/actions/cancel-order", CancelOrderAction)
    adapter.get("/actions/browse-catalog", BrowseCatalogAction)
    return TestClient(adapter.build())


def main() -> None:
    # Guest: NoAuthCoordinator resolves every request to a fixed anonymous Context.
    guest_client = _client_with(NoAuthCoordinator(context=Context()))

    # User: a coordinator that authenticated a real, logged-in manager.
    user_auth = AsyncMock()
    user_auth.process.return_value = Context(user=UserInfo(user_id="alice", roles=(ManagerRole,)))
    user_client = _client_with(user_auth)

    guest_response = guest_client.get("/client-manifest.json")
    user_response = user_client.get("/client-manifest.json")

    print(f"guest status = {guest_response.status_code}")  # 200 — anonymous Context passed auth
    print(f"user  status = {user_response.status_code}")   # 200 — manager passed auth

    guest_body = guest_response.json()
    user_body = user_response.json()

    guest_ops = [endpoint["operation"] for endpoint in guest_body["endpoints"]]
    print(f"guest endpoints          = {guest_ops}")
    # The manager-only endpoint is in the GUEST's catalog too — the manifest is
    # a list of what exists, not a per-role allow-list.
    print(f"manager-only in catalog  = {'POST /actions/cancel-order' in guest_ops}")

    print(f"same manifest_version    = {guest_body['manifest_version'] == user_body['manifest_version']}")
    assert guest_body == user_body  # byte-for-byte identical: the role plays no part
    print(f"guest_body == user_body  = {guest_body == user_body}")

    # The one and only fork: "did auth pass at all". A coordinator whose
    # process() returns None never reaches the manifest — 403 before projection.
    rejected_auth = AsyncMock()
    rejected_auth.process.return_value = None
    rejected_response = _client_with(rejected_auth).get("/client-manifest.json")
    print(f"rejected status          = {rejected_response.status_code}")  # 403 — never reached the manifest
    assert rejected_response.status_code == 403


main()
