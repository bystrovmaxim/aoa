# packages/aoa-fastapi-adapter/tests/test_fastapi_entity_fields.py
"""
FastAPI carries entities in Params and Result end to end.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 4.1, 5.1 and 10.1 of issue #407. A request body with a dictionary id object
and an entity with a relation validates into Params; a Result holding an entity
with a relation, a dictionary reference and a lifecycle goes out in their JSON
forms; the OpenAPI document builds. The adapter's own code does not change.
"""

from __future__ import annotations

from typing import Annotated, Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseStateEntity,
    CompositeOne,
    Lifecycle,
    NoInverse,
    value,
)
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi.adapter import FastApiAdapter


class ApiShopDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "api_shop"
    description = "Entities carried through FastAPI"


@entity(description="Currencies", domain=ApiShopDomain)
class ApiCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="Order state", domain=ApiShopDomain)
class ApiOrderStateEntity(BaseStateEntity):
    """The statuses of an order."""

    receipt_required: bool = Field(default=False, description="Receipt required")
    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid", receipt_required=True)


class ApiOrderLifecycle(Lifecycle[ApiOrderStateEntity]):
    """A draft order is paid."""

    _template = (
        Lifecycle()
        .state(ApiOrderStateEntity.DRAFT)
        .to(ApiOrderStateEntity.PAID)
        .initial()
        .state(ApiOrderStateEntity.PAID)
        .final()
    )


@entity(description="Customer", domain=ApiShopDomain)
class ApiCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Customer id")
    name: str = Field(description="Name")


@entity(description="Order", domain=ApiShopDomain)
class ApiOrderCoreEntity(BaseCoreEntity):
    """An order with a customer, a currency and a lifecycle."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[ApiCustomerCoreEntity], NoInverse()] = Field(description="Customer")
    currency: Annotated[CompositeOne[ApiCurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    lifecycle: ApiOrderLifecycle = Field(description="State")


@meta(description="Stores the api shop entities")
@entities(
    ApiCurrencyEnumEntity,
    ApiCustomerCoreEntity,
    ApiOrderCoreEntity,
)
class ApiShopStorage(BaseStorage):
    """Hold the api shop entities."""


@meta(description="Price an order", domain=ApiShopDomain)
@check_roles(GuestRole)
class PriceOrderAction(BaseAction["PriceOrderAction.Params", "PriceOrderAction.Result"]):
    """Take an order and a currency, return the order."""

    class Params(BaseParams):
        """An order and the currency to price it in."""

        currency: Annotated[CompositeOne[ApiCurrencyEnumEntity], NoInverse()] = Field(description="Currency")
        order: ApiOrderCoreEntity = Field(description="Order")

    class Result(BaseResult):
        """The order, and an id written under an alias."""

        order: ApiOrderCoreEntity = Field(description="Order")
        item_id: int = Field(serialization_alias="itemId", description="Item id")

    @summary_aspect("Return the order")
    async def return_order_summary(
        self, params: PriceOrderAction.Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> PriceOrderAction.Result:
        """Return the order it was given."""
        return PriceOrderAction.Result(order=params.order, item_id=7)


ORDER_JSON: dict[str, Any] = {
    "id": "o1",
    "customer": {"id": "c1", "entity": {"id": "c1", "name": "Ann"}},
    "currency": {"id": "eur"},
    "lifecycle": {"code": "paid"},
}


@pytest.fixture
def client_and_machine() -> tuple[TestClient, ActionProductMachine]:
    """A FastAPI app with the action; the machine's run is replaced, as the adapter's docs advise."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
    adapter.post("/price", PriceOrderAction)
    return TestClient(adapter.build()), machine


def _run_returning_the_order(machine: ActionProductMachine) -> AsyncMock:
    async def run(_context: Any, _action: Any, params: Any, _connections: Any) -> PriceOrderAction.Result:
        return PriceOrderAction.Result(order=params.order, item_id=7)

    machine.run = AsyncMock(side_effect=run)  # type: ignore[method-assign]
    return machine.run


def test_a_request_with_entity_forms_validates(client_and_machine: tuple[TestClient, ActionProductMachine]) -> None:
    """Case 4.1: {"currency": {"id": "eur"}} and an order in its JSON form are accepted."""
    client, machine = client_and_machine
    run = _run_returning_the_order(machine)
    response = client.post("/price", json={"currency": {"id": "eur"}, "order": ORDER_JSON})
    assert response.status_code == 200, response.text
    params = run.call_args.args[2]
    assert params.currency.entity is ApiCurrencyEnumEntity.EUR
    assert params.order.customer.name == "Ann"
    assert params.order.lifecycle == ApiOrderLifecycle("paid")


def test_the_response_carries_the_json_forms(client_and_machine: tuple[TestClient, ActionProductMachine]) -> None:
    """Case 5.1: the relation, the reference and the lifecycle go out in their forms."""
    client, machine = client_and_machine
    _run_returning_the_order(machine)
    body = client.post("/price", json={"currency": {"id": "eur"}, "order": ORDER_JSON}).json()
    assert body["order"]["customer"] == {"id": "c1", "entity": {"id": "c1", "name": "Ann"}}
    assert body["order"]["currency"] == {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}}
    assert body["order"]["lifecycle"] == {
        "code": "paid",
        "display_name": "Paid",
        "properties": {"receipt_required": True},
    }


def test_the_response_reads_back_as_params(client_and_machine: tuple[TestClient, ActionProductMachine]) -> None:
    """What FastAPI writes for the order is accepted back as the order of the next request."""
    client, machine = client_and_machine
    _run_returning_the_order(machine)
    body = client.post("/price", json={"currency": {"id": "eur"}, "order": ORDER_JSON}).json()
    again = client.post("/price", json={"currency": body["order"]["currency"], "order": body["order"]})
    assert again.status_code == 200, again.text
    assert again.json()["order"] == body["order"]


def test_the_openapi_document_builds(client_and_machine: tuple[TestClient, ActionProductMachine]) -> None:
    """Case 5.1: an entity with a lifecycle no longer breaks the whole document."""
    client, _ = client_and_machine
    document = client.app.openapi()
    schemas = document["components"]["schemas"]
    lifecycle_codes = [
        prop["properties"]["code"]["enum"]
        for schema in schemas.values()
        for prop in schema.get("properties", {}).values()
        if isinstance(prop, dict) and "enum" in prop.get("properties", {}).get("code", {})
    ]
    assert ["draft", "paid"] in lifecycle_codes


def test_fastapi_writes_the_serialization_alias(client_and_machine: tuple[TestClient, ActionProductMachine]) -> None:
    """Case 10.1: FastAPI serializes by alias; this test pins the name it writes."""
    client, machine = client_and_machine
    _run_returning_the_order(machine)
    body = client.post("/price", json={"currency": {"id": "eur"}, "order": ORDER_JSON}).json()
    assert body["itemId"] == 7
    assert "item_id" not in body
