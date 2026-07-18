"""
05_manifest_matches_can_via_params_mapper.py — the catalog publishes the shape .can() accepts

A route may register its own request_model + params_mapper, so the shape the
endpoint accepts on the wire ("oid") differs from the action's native Params
("order_id"). The client manifest publishes that ROUTE shape, and POST
/permissions/resolve accepts params in that same shape, running them through the
SAME params_mapper before access_decide. One converter powers both the real call
and the permission check — the client sees one schema in the catalog, not two.

Watch the contrast at the end: the native Params shape ({"order_id": 7}) is not
what the route publishes, so the resolver rejects it (HTTP 400) — the real POST
rejects that same shape too (there as a 422 validation error) — proof that .can()
and the real call share one request_model, not two.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_catalog/05_manifest_matches_can_via_params_mapper.py
"""

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi import FastApiAdapter


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier — the action's native Params field")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


# The ROUTE's own request shape: the field is "oid", not "order_id".
class CancelOrderRequest(BaseModel):
    oid: int = Field(description="Order identifier (route/request field name)")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(GuestRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


def build_app():
    machine = ActionProductMachine()
    adapter = FastApiAdapter(
        machine=machine,
        auth_coordinator=NoAuthCoordinator(context=Context()),
        title="Catalog API",
    )
    # request_model + params_mapper: the wire shape is "oid", mapped to
    # OrderParams(order_id=...). The SAME lambda is what the resolver reuses.
    adapter.post(
        "/actions/cancel-order",
        CancelOrderAction,
        request_model=CancelOrderRequest,
        params_mapper=lambda body: OrderParams(order_id=body.oid),
        tags=["orders"],
    )
    return adapter.build()


def main() -> None:
    client = TestClient(build_app())

    # (a) The catalog publishes the ROUTE shape ("oid"), not the native Params
    #     shape ("order_id"). params_schema is CancelOrderRequest's schema.
    manifest = client.get("/client-manifest.json").json()
    endpoint = next(e for e in manifest["endpoints"] if e["operation"] == "POST /actions/cancel-order")
    params_props = endpoint["params_schema"]["properties"]
    print("── manifest (catalog) ──")
    print(f"operation        = {endpoint['operation']!r}")
    print(f"params_schema    = {sorted(params_props)}")  # ['oid'] — the route shape
    assert "oid" in params_props  # route field, from request_model
    assert "order_id" not in params_props  # native Params field is NOT published

    # (b) The real call accepts {"oid": 7}; the params_mapper turns it into
    #     OrderParams(order_id=7) before the action runs.
    r = client.post("/actions/cancel-order", json={"oid": 7})
    print("\n── real call ──")
    print(f"POST /actions/cancel-order {{'oid': 7}}  -> {r.status_code} {r.json()}")
    assert r.status_code == 200

    # (c) .can(): POST /permissions/resolve accepts params in THAT same shape.
    #     The resolver runs {"oid": 7} through the SAME params_mapper before
    #     access_decide — a verdict comes back, not a validation error.
    r = client.post(
        "/permissions/resolve",
        json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"oid": 7}}]},
    )
    result = r.json()["results"][0]
    print("\n── .can() via POST /permissions/resolve ──")
    print(f"params {{'oid': 7}}      -> {r.status_code} result={result}")
    assert r.status_code == 200
    assert result["kind"] == "success"  # guest passes GuestRole → success

    # (d) The native Params shape is NOT what the route publishes, so validating
    #     {"order_id": 7} against CancelOrderRequest fails ("oid" is required) before
    #     the params_mapper ever runs. Unlike an unknown operation (which isolates to
    #     its own CHECK_ERROR result), a known endpoint's params failing validation
    #     fails the WHOLE request with HTTP 400 — see resolve_verdicts()'s docstring.
    r = client.post(
        "/permissions/resolve",
        json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
    )
    print("\n── wrong (native) shape is rejected ──")
    print(f"params {{'order_id': 7}}  -> {r.status_code} (route shape is 'oid', not 'order_id')")
    assert r.status_code == 400


if __name__ == "__main__":
    main()
