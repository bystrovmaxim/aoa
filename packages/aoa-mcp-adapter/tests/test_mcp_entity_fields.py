# packages/aoa-mcp-adapter/tests/test_mcp_entity_fields.py
"""
MCP carries entities in Params and Result end to end.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 4.2 and 10.1 of issue #407. A tool input with a dictionary id object and an
entity with a relation validates into Params, the tool's input schema builds, and
the result goes out in the JSON forms under the fields' own names. The adapter's
own code does not change.
"""

from __future__ import annotations

import json
from typing import Annotated
from unittest.mock import AsyncMock

import pytest
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
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections, InMemoryDataSource
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.mcp.adapter import McpAdapter, _serialize_result, _validate_tool_request_kwargs
from aoa.mcp.route_record import McpRouteRecord


class McpShopDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "mcp_shop"
    description = "Entities carried through MCP"


@meta(description="Where McpShopStorage keeps its rows")
class McpShopDataSource(InMemoryDataSource):
    """The store McpShopStorage works with."""


@meta(description="Stores the mcp shop entities", domain=McpShopDomain)
class McpShopStorage(BaseStorage[McpShopDataSource]):
    """Hold the mcp shop entities."""


@entity(description="Currencies", resource=McpShopStorage)
class McpCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")


@entity(description="Order state", resource=McpShopStorage)
class McpOrderStateEntity(BaseStateEntity):
    """The statuses of an order."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


class McpOrderLifecycle(Lifecycle[McpOrderStateEntity]):
    """A draft order is paid."""

    _template = (
        Lifecycle()
        .state(McpOrderStateEntity.DRAFT)
        .to(McpOrderStateEntity.PAID)
        .initial()
        .state(McpOrderStateEntity.PAID)
        .final()
    )


@entity(description="Customer", resource=McpShopStorage)
class McpCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Customer id")
    name: str = Field(description="Name")


@entity(description="Order", resource=McpShopStorage)
class McpOrderCoreEntity(BaseCoreEntity):
    """An order with a customer, a currency and a lifecycle."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[McpCustomerCoreEntity], NoInverse()] = Field(description="Customer")
    currency: Annotated[CompositeOne[McpCurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    lifecycle: McpOrderLifecycle = Field(description="State")


@meta(description="Price an order over MCP", domain=McpShopDomain)
@check_roles(GuestRole)
class McpPriceOrderAction(BaseAction["McpPriceOrderAction.Params", "McpPriceOrderAction.Result"]):
    """Take an order and a currency, return the order."""

    class Params(BaseParams):
        """An order and the currency to price it in."""

        currency: Annotated[CompositeOne[McpCurrencyEnumEntity], NoInverse()] = Field(description="Currency")
        order: McpOrderCoreEntity = Field(description="Order")

    class Result(BaseResult):
        """The order, and an id with a serialization alias."""

        order: McpOrderCoreEntity = Field(description="Order")
        item_id: int = Field(serialization_alias="itemId", description="Item id")

    @summary_aspect("Return the order")
    async def return_order_summary(
        self, params: McpPriceOrderAction.Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> McpPriceOrderAction.Result:
        """Return the order it was given."""
        return McpPriceOrderAction.Result(order=params.order, item_id=7)


ORDER_JSON = {
    "id": "o1",
    "customer": {"id": "c1", "entity": {"id": "c1", "name": "Ann"}},
    "currency": {"id": "eur"},
    "lifecycle": {"code": "paid"},
}


def test_a_tool_input_with_entity_forms_validates() -> None:
    """Case 4.2: the dictionary id object and the order's forms validate into Params."""
    params = _validate_tool_request_kwargs({"currency": {"id": "eur"}, "order": ORDER_JSON}, McpPriceOrderAction.Params)
    assert params.currency.entity is McpCurrencyEnumEntity.EUR
    assert repr(params.currency) == "CompositeOne(id='eur', loaded)"
    assert params.order.customer.name == "Ann"
    assert params.order.lifecycle == McpOrderLifecycle("paid")


def test_the_result_goes_out_in_the_json_forms_under_field_names() -> None:
    """Case 10.1: MCP writes the fields under their own names; the forms are the same as everywhere."""
    params = _validate_tool_request_kwargs({"currency": {"id": "eur"}, "order": ORDER_JSON}, McpPriceOrderAction.Params)
    record = McpRouteRecord(action_class=McpPriceOrderAction, tool_name="price_order")
    payload = _serialize_result(
        McpPriceOrderAction.Result(order=params.order, item_id=7), record, has_response_mapper=False
    )
    assert payload["item_id"] == 7
    assert "itemId" not in payload
    assert payload["order"]["customer"] == {"id": "c1", "entity": {"id": "c1", "name": "Ann"}}
    assert payload["order"]["currency"]["code"] == "eur"
    assert payload["order"]["lifecycle"] == {"code": "paid", "display_name": "Paid", "properties": {}}
    json.dumps(payload)


@pytest.mark.asyncio
async def test_the_tool_input_schema_builds() -> None:
    """The tool's input schema describes the order and the currency."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    server = McpAdapter(machine=machine, auth_coordinator=auth).tool("price_order", McpPriceOrderAction).build()
    tool = next(t for t in await server.list_tools() if t.name == "price_order")
    properties = (tool.inputSchema or {}).get("properties") or {}
    assert {"currency", "order"} <= set(properties)
    assert "anyOf" in json.dumps(properties["currency"])
