"""
03_manifest_no_guard_body_leak.py — a condition body cannot leak into the catalog

GET /client-manifest.json is projected from route records (method, path, action
class, request/response models) — never from the action's function bodies. So an
action whose guard= and access_decide each hide a unique sentinel string can be
serialized in full, and neither sentinel appears anywhere in the output: there is
structurally nothing to leak, not a filter that strips it. This is the regression
guarding the API-surface-leak risk.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/03_manifest_no_guard_body_leak.py
"""

import json

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi.adapter import FastApiAdapter

# Sentinels: each lives ONLY inside one condition body, nowhere in @meta or the
# param/result schemas. If either appears in the manifest, a body has leaked.
_GUARD_SENTINEL = "guard-body-sentinel-b7c204"
_DECIDE_SENTINEL = "decide-body-sentinel-e5d613"


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class StaffRole(ApplicationRole):
    name = "staff"
    description = "Store staff"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


# ---------------------------------------------------------------------------
# One fully gated action: a guard= over the role, plus an object-level
# access_decide. Each condition references a sentinel that appears nowhere in
# @meta (description/domain), the role name, or the Params/Result schemas.
# ---------------------------------------------------------------------------

@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(
    StaffRole,
    guard=lambda user, params: str(params.order_id) != _GUARD_SENTINEL,
    reason=FailSecurityVerdict("order not eligible"),
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    async def access_decide(
        self,
        params: OrderParams,
        context: Context,
        box: ToolsBox,
        connections: dict,
    ) -> FailSecurityVerdict | AllowedVerdict:
        secret_token = _DECIDE_SENTINEL  # lives only in this method body, never in a returned value
        if secret_token != str(params.order_id):
            return AllowedVerdict()
        return FailSecurityVerdict("order rejected by access_decide")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


# ---------------------------------------------------------------------------
# Build a real adapter and fetch the catalog over HTTP. NoAuthCoordinator yields
# an open guest context (200); the manifest is role-independent, so the StaffRole
# gate on the action does not change what the endpoint returns.
# ---------------------------------------------------------------------------

def main() -> None:
    adapter = FastApiAdapter(
        machine=ActionProductMachine(loggers=[]),
        auth_coordinator=NoAuthCoordinator(context=Context()),
    )
    adapter.post("/actions/cancel-order", CancelOrderAction)
    client = TestClient(adapter.build())

    manifest = client.get("/client-manifest.json").json()
    blob = json.dumps(manifest)  # the entire wire payload, serialized

    endpoint = manifest["endpoints"][0]
    print(f"operation               = {endpoint['operation']!r}")
    print(f"entry keys              = {sorted(endpoint)}")
    print(f"params_schema props     = {sorted(endpoint['params_schema']['properties'])}")
    print(f"guard sentinel present  = {_GUARD_SENTINEL in blob}")
    print(f"decide sentinel present = {_DECIDE_SENTINEL in blob}")

    # The guarantee is structural: route records carry no condition bodies, so
    # there is nothing to serialize and nothing to strip.
    assert _GUARD_SENTINEL not in blob
    assert _DECIDE_SENTINEL not in blob
    print("OK — no condition body leaked into the manifest")


main()
