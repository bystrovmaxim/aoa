# packages/aoa-action-machine/tests/action_machine/graph/test_relation_optional.py
"""
A relation says whether it may hold nothing (spec 029, FR-043).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A diagram draws an optional relation end (zero or one) differently from a mandatory
one (exactly one). The relation row carries ``optional``: true when the field's
annotation admits ``None`` or it defaults to ``None``; the relation edge ships it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    entity class ──gather_entity_relation_intent_resolvers──► rows (optional)
                 ──EntityGraphEdge──► properties.optional
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_relation_intent_resolver import gather_entity_relation_intent_resolvers


class _OptionalDomain(BaseDomain):
    name = "optional_relations"
    description = "Fixtures for optional relation ends"


@exclude_graph_model
@entity(description="A currency", domain=_OptionalDomain)
class _OptionalCurrencyEnumEntity(BaseEnumEntity):
    """Two codes, as a dictionary has."""

    EUR = value(code="eur", display_name="Euro")
    USD = value(code="usd", display_name="Dollar")


@exclude_graph_model
@entity(description="An order", domain=_OptionalDomain)
class _OptionalOrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Identifier")
    billed_in: Annotated[AssociationOne[_OptionalCurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="May be empty"
    )
    priced_in: Annotated[AssociationOne[_OptionalCurrencyEnumEntity], NoInverse()] = Field(description="Always set")


def test_a_relation_that_may_be_empty_is_optional_and_one_that_may_not_is_not() -> None:
    """``X | None`` with a ``None`` default is optional; a plain relation is mandatory."""
    rows = {row.field_name: row for row in gather_entity_relation_intent_resolvers(_OptionalOrderCoreEntity)}
    assert (rows["billed_in"].cardinality, rows["billed_in"].optional) == ("one", True)
    assert (rows["priced_in"].cardinality, rows["priced_in"].optional) == ("one", False)
