"""
01_registered_action_in_manifest.py — a registered action shows up in the catalog

``GET /client-manifest.json`` is a pure projection of the routes you registered
on the adapter: register an action with ``adapter.post(path, ActionClass)`` and
it appears as one manifest endpoint, keyed by ``operation = "{METHOD} {path}"``,
carrying the full JSON Schema of its Params and Result. No graph traversal, no
Context, no role filtering — the same manifest goes to every caller, so this is
the happy path every other catalog example builds on.

Watch the operation string: it is literally ``"POST /actions/cancel-order"`` —
method and path joined with a space, the path template kept verbatim (a
``{order_id}`` placeholder would stay a placeholder, never substituted).

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/01_registered_action_in_manifest.py
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


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


def main() -> None:
    # Build an adapter, register exactly ONE action, and expose the app.
    # NoAuthCoordinator(context=Context()) resolves an anonymous (guest) Context,
    # which is all the manifest endpoint needs — the catalog is role-independent.
    adapter = FastApiAdapter(
        machine=ActionProductMachine(loggers=[]),
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )
    adapter.post("/actions/cancel-order", CancelOrderAction)

    client = TestClient(adapter.build())
    manifest = client.get("/client-manifest.json").json()

    # A versioned list of endpoints, one per registered route.
    print(f"version                  = {manifest['version']}")
    print(f"manifest_schema_version  = {manifest['manifest_schema_version']}")
    print(f"endpoint count           = {len(manifest['endpoints'])}")

    entry = manifest["endpoints"][0]
    print(f"operation        = {entry['operation']!r}")
    print(f"route            = {entry['route']}")
    print(f"params_schema    = required={entry['params_schema'].get('required')} "
          f"properties={list(entry['params_schema']['properties'])}")
    print(f"result_schema    = properties={list(entry['result_schema']['properties'])}")

    # The one action we registered is the one endpoint in the catalog, keyed by
    # "{METHOD} {path}", and its params_schema carries the declared field.
    assert len(manifest["endpoints"]) == 1
    assert entry["operation"] == "POST /actions/cancel-order"
    assert entry["route"] == {"method": "POST", "path": "/actions/cancel-order"}
    assert "order_id" in entry["params_schema"]["properties"]
    assert "status" in entry["result_schema"]["properties"]
    print("\nOK — the registered action appears in the manifest with full schema.")


main()
