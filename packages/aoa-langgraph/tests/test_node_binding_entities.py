# packages/aoa-langgraph/tests/test_node_binding_entities.py
"""
A LangGraph node returns a Result that holds an entity with a dictionary reference.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 1.3 of issue #405: the node binding calls ``result.model_dump()``, which
works once a relation container no longer forwards Pydantic's protocol names.
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain, BaseEnumEntity, CompositeOne, NoInverse, value
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


class _PriceParams(BaseParams):
    """Empty input."""


class _PriceResult(BaseResult):
    """A Result that holds the price."""

    price: NodePriceCoreEntity = Field(description="Price")


class _Box:
    """A box whose run returns the Result directly."""

    async def run(self, action_cls: Any, params: Any, connections: Any = None) -> _PriceResult:
        """Return the Result an action would return."""
        return _PriceResult(price=NodePriceCoreEntity(id="p1", currency=CompositeOne(id="eur")))


class _State(BaseModel):
    """The graph state with one key."""

    price: Any = None


@pytest.mark.asyncio
async def test_a_node_returns_an_entity_with_a_dictionary_reference() -> None:
    """Case 1.3: the node returns the Result's fields, the container included."""
    out = await _run_action_node(object, lambda _state: _PriceParams(), None, None, _Box(), _State())  # type: ignore[arg-type]
    assert out["price"]["id"] == "p1"
    assert isinstance(out["price"]["currency"], CompositeOne)
    assert out["price"]["currency"].entity is NodeCurrencyEnumEntity.EUR
