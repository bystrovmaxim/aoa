# tests/action_machine/graph/test_entity_domain_declaration.py
"""
The entity names its own domain: ``@entity(description, domain=...)``.

Covers the declaration (a domain is read from the entity's own ``_entity_info``), the
refusals (a missing or non-``BaseDomain`` domain, and the removed ``resource=`` argument),
and a built graph that carries an entity→domain edge and no entity→resource edge.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
from aoa.action_machine.domain.exceptions import EntityDecoratorError
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver

from ...support.isolated_entity_models import run_isolated_model


class _DeclaredDomain(BaseDomain):
    """The domain the entity declares for itself."""

    name = "declared"
    description = "Declared"


@entity(description="An order that names its domain", domain=_DeclaredDomain)
class _DeclaredOrderCoreEntity(BaseCoreEntity):
    """An entity that declares its own domain."""

    id: str = Field(description="Order id")


def test_the_domain_is_read_from_the_entity() -> None:
    """The declaration writes ``description`` and ``domain``; the resolver returns that domain."""
    assert _DeclaredOrderCoreEntity._entity_info == {
        "description": "An order that names its domain",
        "domain": _DeclaredDomain,
    }
    assert EntityIntentResolver.resolve_domain_type(_DeclaredOrderCoreEntity) is _DeclaredDomain


def test_a_subclass_inherits_the_declared_domain() -> None:
    """A subclass with no ``@entity`` of its own inherits its parent's declared domain."""

    class RushOrderCoreEntity(_DeclaredOrderCoreEntity):  # type: ignore[misc, valid-type]
        """A rush order."""

    assert EntityIntentResolver.resolve_domain_type(RushOrderCoreEntity) is _DeclaredDomain


def test_a_missing_domain_is_refused() -> None:
    """``domain`` is keyword-only and required: the signature refuses its absence."""
    with pytest.raises(TypeError, match="domain"):
        entity(description="No domain")  # type: ignore[call-arg]


@pytest.mark.parametrize("domain", [None, object, "declared"])
def test_a_non_base_domain_is_refused(domain: object) -> None:
    """Anything but a ``BaseDomain`` subclass is refused at declaration time."""
    with pytest.raises(EntityDecoratorError, match="BaseDomain subclass"):
        entity(description="Wrong domain", domain=domain)  # type: ignore[arg-type]


def test_the_resource_argument_is_refused() -> None:
    """The removed ``resource=`` keyword is refused by the signature itself."""
    with pytest.raises(TypeError, match="unexpected keyword argument 'resource'"):
        entity(description="Old form", domain=_DeclaredDomain, resource=object)  # type: ignore[call-arg]


_MODEL = textwrap.dedent(
    """
    import json

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
    from aoa.action_machine.intents.entity import entity


    class OrderDomain(BaseDomain):
        name = "order"
        description = "Order"


    @entity(description="Customer order", domain=OrderDomain)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")


    print(create_node_graph_coordinator().to_json())
    """
)


def _built_graph() -> dict[str, Any]:
    """The graph of one entity that declares its own domain, built in a fresh interpreter."""
    result = run_isolated_model(_MODEL)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_a_built_graph_has_the_entity_domain_edge_and_no_entity_resource_edge() -> None:
    """The entity reaches its own domain; no ``entity_resource`` edge exists."""
    graph = _built_graph()
    entity_id = next(node["id"] for node in graph["nodes"] if node["label"] == "SalesOrderCoreEntity")
    (domain_edge,) = [edge for edge in graph["edges"] if edge["source_id"] == entity_id and edge["type"] == "domain"]
    assert domain_edge["target_id"].endswith("OrderDomain")
    assert [edge for edge in graph["edges"] if edge["type"] == "entity_resource"] == []
