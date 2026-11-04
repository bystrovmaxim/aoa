# packages/aoa-langgraph/tests/test_node_binding_entities.py
"""
A LangGraph node returns a Result that holds an entity with a dictionary reference.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 1.3 of issues #405 and #407: the node binding calls ``result.model_dump()``,
Pydantic's Python mode, which keeps relation containers and lifecycles as they
are and writes each field under its own name (case 10.1).
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field

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
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.langgraph.node_binding import _run_action_node


class _NodeDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "node_binding_entities"
    description = "Entities for the LangGraph node binding test"


@entity(description="Currencies", domain=_NodeDomain)
class NodeCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    EUR = value(code="eur", display_name="Euro")


@entity(description="Price", domain=_NodeDomain)
class NodePriceCoreEntity(BaseCoreEntity):
    """A price with a dictionary reference."""

    id: str = Field(description="Id")
    currency: Annotated[CompositeOne[NodeCurrencyEnumEntity], NoInverse()] = Field(description="Currency")


@entity(description="Customer", domain=_NodeDomain)
class NodeCustomerCoreEntity(BaseCoreEntity):
    """A customer."""

    id: str = Field(description="Id")
    name: str = Field(description="Name")


@entity(description="Order state", domain=_NodeDomain)
class NodeOrderStateEntity(BaseStateEntity):
    """The statuses of an order."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


class NodeOrderLifecycle(Lifecycle[NodeOrderStateEntity]):
    """A draft order is paid."""

    _template = (
        Lifecycle()
        .state(NodeOrderStateEntity.DRAFT)
        .to(NodeOrderStateEntity.PAID)
        .initial()
        .state(NodeOrderStateEntity.PAID)
        .final()
    )


@entity(description="Order", domain=_NodeDomain)
class NodeOrderCoreEntity(BaseCoreEntity):
    """An order with a customer and a lifecycle."""

    id: str = Field(description="Id")
    customer: Annotated[AssociationOne[NodeCustomerCoreEntity], NoInverse()] = Field(description="Customer")
    lifecycle: NodeOrderLifecycle = Field(description="State")


class _PriceParams(BaseParams):
    """Empty input."""


class _PriceResult(BaseResult):
    """A Result that holds the price."""

    price: NodePriceCoreEntity = Field(description="Price")
    order: NodeOrderCoreEntity | None = Field(default=None, description="Order")
    item_id: int = Field(default=7, serialization_alias="itemId", description="Item id")


class _Box:
    """A box whose run returns the Result directly."""

    async def run(self, action_cls: Any, params: Any, connections: Any = None) -> _PriceResult:
        """Return the Result an action would return."""
        return _PriceResult(
            price=NodePriceCoreEntity(id="p1", currency=CompositeOne(id="eur")),
            order=NodeOrderCoreEntity.model_validate(
                {"id": "o1", "customer": {"id": "c1"}, "lifecycle": {"code": "paid"}}
            ),
        )


class _State(BaseModel):
    """The graph state with one key."""

    price: Any = None
    order: Any = None
    item_id: Any = None


@pytest.mark.asyncio
async def test_a_node_returns_an_entity_with_a_dictionary_reference() -> None:
    """Case 1.3: the node returns the Result's fields, the container included."""
    out = await _run_action_node(object, lambda _state: _PriceParams(), None, None, _Box(), _State())  # type: ignore[arg-type]
    assert out["price"]["id"] == "p1"
    assert isinstance(out["price"]["currency"], CompositeOne)
    assert out["price"]["currency"].entity is NodeCurrencyEnumEntity.EUR


@pytest.mark.asyncio
async def test_a_node_returns_an_entity_with_a_relation_and_a_lifecycle() -> None:
    """Case 1.3: the state receives the container and the lifecycle themselves."""
    out = await _run_action_node(object, lambda _state: _PriceParams(), None, None, _Box(), _State())  # type: ignore[arg-type]
    assert isinstance(out["order"]["customer"], AssociationOne)
    assert out["order"]["customer"].id == "c1"
    assert out["order"]["lifecycle"] == NodeOrderLifecycle("paid")


@pytest.mark.asyncio
async def test_a_node_writes_fields_under_their_own_names() -> None:
    """Case 10.1: LangGraph's state uses the field name, not the serialization alias."""
    out = await _run_action_node(object, lambda _state: _PriceParams(), None, None, _Box(), _State())  # type: ignore[arg-type]
    assert out["item_id"] == 7
    assert "itemId" not in out
