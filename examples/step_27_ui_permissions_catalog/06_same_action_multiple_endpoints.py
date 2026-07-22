"""
06_same_action_multiple_endpoints.py — the catalog lists endpoints, not actions

One action class bound to several routes produces one independent manifest entry
*per route*, keyed by ``operation = "{METHOD} {path}"``. Register the same action
on POST and GET of the same path and the manifest carries two entries — same class,
distinct operations — with no dedup and no error.

Registering the identical method+path twice is a different story: same ``operation``,
so it is first-wins like Starlette's router. build_route_index() (what actually
dispatches a resolve request) keeps the first record and drops the second — again
not an error, the second route was simply unreachable.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/06_same_action_multiple_endpoints.py
"""

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter
from aoa.fastapi.permissions import build_route_index
from aoa.fastapi.route_record import FastApiRouteRecord


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(GuestRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


@meta(description="Refund an order", domain=StoreDomain)
@check_roles(GuestRole)
class RefundOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Refund the order")
    async def refund_summary(self, params, state, box, connections):
        return OrderResult(status="refunded")


def main() -> None:
    # ── Part 1: one action, two routes → two independent endpoints ──
    adapter = FastApiAdapter(
        machine=ActionProductMachine(loggers=[]),
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )
    # Same path, different method — two distinct operations for ONE action class.
    adapter.post("/actions/cancel-order", CancelOrderAction)
    adapter.get("/actions/cancel-order", CancelOrderAction)

    client = TestClient(adapter.build())
    manifest = client.get("/client-manifest.json").json()

    operations = [endpoint["operation"] for endpoint in manifest["endpoints"]]
    names = [endpoint["name"] for endpoint in manifest["endpoints"]]

    print("── one action on two routes ──")
    print(f"operations = {operations}")  # ['POST /actions/cancel-order', 'GET /actions/cancel-order']
    print(f"names      = {names}")  # ['CancelOrderAction', 'CancelOrderAction'] — same class, twice
    print(f"entries    = {len(manifest['endpoints'])}")  # 2 — the catalog keys by endpoint, not action

    assert operations == ["POST /actions/cancel-order", "GET /actions/cancel-order"]
    assert names == ["CancelOrderAction", "CancelOrderAction"]
    assert len(manifest["endpoints"]) == 2

    # ── Part 2: same method+path registered twice → first-wins, not an error ──
    first = FastApiRouteRecord(action_class=CancelOrderAction, method="post", path="/a")
    second = FastApiRouteRecord(action_class=RefundOrderAction, method="post", path="/a")

    # Both records share the SAME operation "POST /a". build_route_index() keeps the
    # first and drops the second — silently, exactly like Starlette's router (the
    # second registration is unreachable in HTTP routing anyway), never an error.
    index = build_route_index([first, second])

    print("\n── same operation registered twice ──")
    print(f"index size          = {len(index)}")  # 1 — deduplicated by operation
    print(f"POST /a resolves to = {index['POST /a'].action_class.__name__}")  # CancelOrderAction (the first)

    assert len(index) == 1
    assert index["POST /a"].action_class is CancelOrderAction  # first-wins


main()
