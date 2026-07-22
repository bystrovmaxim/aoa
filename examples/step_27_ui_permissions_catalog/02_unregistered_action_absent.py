"""
02_unregistered_action_absent.py — registration, not decoration, decides existence

Two actions are defined identically — same @meta, same @check_roles, same
Params/Result, same @summary_aspect. Only one is registered on the adapter with
``adapter.post(...)``. The client manifest lists exactly the registered
endpoint; the fully-decorated but never-registered action is simply absent.

The invariant: an action exists for the frontend only when a route
(.post/.get/...) registers it. No decorator and no flag conjures an action into
the manifest on its own — ``build_manifest`` projects ``self._routes`` and
nothing else, so an action that never became a route record cannot appear.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/02_unregistered_action_absent.py
"""

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, NoAuthCoordinator
from aoa.action_machine.context import Context
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


# Two actions, decorated identically down to the aspect. The ONLY thing that
# differs is whether a route registers them in main() below.


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


@meta(description="Archive an order", domain=StoreDomain)
@check_roles(ManagerRole)
class ArchiveOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Archive the order")
    async def archive_summary(self, params, state, box, connections):
        return OrderResult(status="archived")


def main() -> None:
    adapter = FastApiAdapter(
        machine=ActionProductMachine(loggers=[]),
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )

    # Register exactly ONE of the two. ArchiveOrderAction is never handed to a
    # route method, so no route record is ever created for it.
    adapter.post("/actions/cancel-order", CancelOrderAction)

    client = TestClient(adapter.build())
    manifest = client.get("/client-manifest.json").json()

    operations = [endpoint["operation"] for endpoint in manifest["endpoints"]]
    names = [endpoint["name"] for endpoint in manifest["endpoints"]]

    print(f"version          = {manifest['version']}")
    print(f"endpoint count   = {len(manifest['endpoints'])}")
    print(f"operations       = {operations}")
    print(f"action names     = {names}")

    # The registered action is present, keyed by "{METHOD} {path}".
    assert operations == ["POST /actions/cancel-order"]
    assert "CancelOrderAction" in names

    # The fully-decorated but never-registered action is absent — decoration
    # alone never puts an action in the manifest.
    assert "ArchiveOrderAction" not in names

    print()
    print("CancelOrderAction  -> registered     -> in manifest")
    print("ArchiveOrderAction -> not registered -> absent")
    print("OK — registration, not decoration, decides what the frontend sees.")


main()
