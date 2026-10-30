# packages/maxitor/core/graph_compare/src/maxitor/graph_compare/edge_ids.py
"""
Edge ids — the id a graph of version ``1.0`` would have written on each edge.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

From ``1.1`` on, every edge carries its ``id``; a ``1.0`` graph's edges carry none.
To compare a ``1.0`` graph with any other, each of its edges gets the id the ``1.1``
export would write for it (issue #285):

- by default ``<source_id>|<type>|<target_id>``;
- ``entity_relation`` is named by its field: ``<source_id>|entity_relation|<field_name>``,
  so a relation that starts pointing at another entity keeps its id;
- ``lifecycle_transition`` appends the state it leaves: ``…|<target_id>|<from_state>``.

This is a copy of AOA's rule (``aoa.action_machine.graph.edge_identity``): this
module may not import AOA. The front's suite checks the two give the same id for
every edge of the demo's graph (``test_edge_rule_in_step.py``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    edge row (1.0) ──► source, type, target or member, suffix ──► "a|type|b[|suffix]"
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from maxitor.graph_compare.comparison import GraphNotComparableError

SEPARATOR = "|"
"""What joins the parts of an edge id; no part may contain it."""

_MEMBER: Mapping[str, str] = {"entity_relation": "field_name"}
"""Edge types whose id names a property of the edge in place of its target."""

_SUFFIX: Mapping[str, str] = {"lifecycle_transition": "from_state"}
"""Edge types whose id appends a property of the edge after its target."""


def _part(value: Any, edge_type: str, field: str) -> str:
    """Return ``value`` as one id part, or refuse naming the type and the field."""
    if not isinstance(value, str) or not value:
        raise GraphNotComparableError(f"Edge of type {edge_type!r}: {field!r} is missing, empty or not a string.")
    if SEPARATOR in value:
        raise GraphNotComparableError(f"Edge of type {edge_type!r}: {field!r} contains {SEPARATOR!r}: {value!r}.")
    return value


def edge_id(row: Mapping[str, Any]) -> str:
    """
    AI-CORE-BEGIN
    ROLE: The id of one edge row as the ``1.1`` export would write it.
    CONTRACT: Reads ``source_id``, ``type``, ``target_id`` and, for the two special types, one property; any ``id`` already in the row is ignored.
    INVARIANTS: Pure; the same row always gives the same id, equal to AOA's ``edge_id``.
    FAILURES: ``GraphNotComparableError`` naming the type and the field when a part is missing, empty, not a string, or contains ``|``.
    AI-CORE-END
    """
    raw_type = row.get("type")
    edge_type = _part(raw_type, str(raw_type), "type")
    source = _part(row.get("source_id"), edge_type, "source_id")
    target = _part(row.get("target_id"), edge_type, "target_id")
    properties = row.get("properties") or {}
    member = _MEMBER.get(edge_type)
    if member is not None:
        target = _part(properties.get(member), edge_type, member)
    parts = [source, edge_type, target]
    suffix = _SUFFIX.get(edge_type)
    if suffix is not None:
        parts.append(_part(properties.get(suffix), edge_type, suffix))
    return SEPARATOR.join(parts)
