# src/action_machine/domain/domain_graph_vertex.py
"""
DomainGraphVertex — interchange projection for BaseDomain marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.graph_vertex.GraphVertex` view derived
from a ``BaseDomain`` subclass **without** retaining a reference to that class on
the vertex instance. All interchange data lives in ``id``, ``node_type``,
``label``, and ``properties`` only.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[BaseDomain]
              │
              v
    DomainGraphVertex.__init__  ──calls──>  DomainGraphVertex.parse(domain_cls)
              │
              v
    ParsedGraphVertex  ──feeds──>  frozen GraphVertex(id, node_type, label, properties)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The domain class is never stored on :class:`DomainGraphVertex` instances.
- ``parse`` reads only ``name`` / ``description`` class attributes (same contract as
  domain materialization in ``ApplicationContextInspector``).
- ``BaseDomain`` itself is not a valid parse target (abstract marker).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class ShopDomain(BaseDomain):
        name = \"shop\"
        description = \"Shop context\"

    v = DomainGraphVertex(ShopDomain)
    assert v.node_type == \"Domain\"

Edge case::

    GraphVertex.parse(object())  # raises GraphVertexParseError

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- :meth:`DomainGraphVertex.parse` raises ``TypeError`` / ``ValueError`` when the
  object is not a concrete ``BaseDomain`` subclass or ``name``/``description``
  are missing or blank.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Domain-scoped GraphVertex bridge for BaseDomain subclasses.
CONTRACT: Construct from type[BaseDomain]; interchange fields via parse; no domain reference stored.
INVARIANTS: Immutable vertex; parse aligns with ApplicationContextInspector domain rows.
FLOW: domain class -> parse -> ParsedGraphVertex -> frozen GraphVertex fields.
FAILURES: GraphVertexParseError on base parse; TypeError/ValueError on invalid domain.
EXTENSION POINTS: Other graph vertex specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_vertex import GraphVertex, ParsedGraphVertex
from action_machine.interchange_vertex_labels import DOMAIN_VERTEX_TYPE


@dataclass(init=False, frozen=True)
class DomainGraphVertex(GraphVertex):
    """
    AI-CORE-BEGIN
    ROLE: Interchange vertex for a bounded-context domain marker.
    CONTRACT: Built from type[BaseDomain] via parse; does not keep the domain type.
    INVARIANTS: Same naming and meta rules as ApplicationContextInspector domain facet.
    AI-CORE-END
    """

    def __init__(self, domain_cls: type[BaseDomain]) -> None:
        parsed = type(self).parse(domain_cls)
        super().__init__(
            id=parsed.id,
            node_type=parsed.node_type,
            label=parsed.label,
            properties=dict(parsed.properties),
        )

    @classmethod
    def parse(cls, obj: object) -> ParsedGraphVertex:
        """
        Build interchange fields from a concrete ``BaseDomain`` subclass.

        The domain class is read only for this call and not retained on the
        resulting vertex instance.

        Raises:
            TypeError: ``obj`` is not a concrete ``BaseDomain`` subclass type.
            ValueError: ``name`` / ``description`` are not valid non-blank strings.
        """
        if obj is BaseDomain:
            msg = f"parse() does not accept the abstract {BaseDomain.__name__!r} marker."
            raise TypeError(msg)
        if not isinstance(obj, type) or not issubclass(obj, BaseDomain):
            msg = f"Expected a BaseDomain subclass type, got {obj!r}"
            raise TypeError(msg)

        name = getattr(obj, "name", None)
        description = getattr(obj, "description", None)
        if not isinstance(name, str) or not isinstance(description, str):
            msg = (
                f"Domain class {obj.__qualname__!r} must define non-empty "
                f"str class attributes 'name' and 'description'."
            )
            raise ValueError(msg)
        if not name.strip() or not description.strip():
            msg = (
                f"Domain class {obj.__qualname__!r} must have non-blank "
                f"'name' and 'description'."
            )
            raise ValueError(msg)

        vertex_id = BaseIntentInspector._make_node_name(obj)
        return ParsedGraphVertex(
            id=vertex_id,
            node_type=DOMAIN_VERTEX_TYPE,
            label=name.strip(),
            properties={"name": name, "description": description},
        )
