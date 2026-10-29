# packages/aoa-action-machine/src/aoa/action_machine/graph/edge_identity.py
"""
Edge identity — the id of one exported graph edge, computed from its row.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two versions of a graph are compared edge by edge, so every exported edge needs an
id that stays the same for the same edge. :func:`edge_id` computes it from the fields
the edge row already carries:

- by default ``<source_id>|<type>|<target_id>``;
- ``entity_relation`` is named by its field: ``<source_id>|entity_relation|<field_name>``,
  so a relation that starts pointing at another entity keeps its id;
- ``lifecycle_transition`` appends the state it leaves: ``…|<target_id>|<from_state>``.

The export writes the id it computes here, and a reader of an older file (format
``1.0``, no ``id``) computes the same id from the same row.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    EntityGraphEdge / StateGraphEdge  (EDGE_TYPE, ID_RULE)
                    │
                    ▼
              EDGE_ID_RULES  ──►  edge_id(row)  ──►  NodeGraphCoordinator.build / to_json
                                        └──────────►  readers of exported files

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    edge_id({"source_id": "a.Offer", "type": "entity_relation", "target_id": "a.Item",
             "properties": {"field_name": "items"}})
    # 'a.Offer|entity_relation|items'
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from aoa.action_machine.graph.core.edge_id_rule import EDGE_SEPARATOR, EdgeIdRule
from aoa.action_machine.graph.edges.entity_graph_edge import EntityGraphEdge
from aoa.action_machine.graph.edges.state_graph_edge import StateGraphEdge

__all__ = ["EDGE_ID_RULES", "EDGE_SEPARATOR", "EdgeIdRule", "edge_id"]

EDGE_ID_RULES: Mapping[str, EdgeIdRule] = MappingProxyType(
    {cls.EDGE_TYPE: cls.ID_RULE for cls in (EntityGraphEdge, StateGraphEdge)},
)


def _part(value: Any, edge_type: str, field: str) -> str:
    """Return ``value`` as one id part, or raise naming the type and the field."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"Edge of type {edge_type!r}: {field!r} is missing, empty or not a string.")
    if EDGE_SEPARATOR in value:
        raise ValueError(f"Edge of type {edge_type!r}: {field!r} contains {EDGE_SEPARATOR!r}: {value!r}.")
    return value


def edge_id(row: Mapping[str, Any]) -> str:
    """
    AI-CORE-BEGIN
    ROLE: Single source of the id of an exported edge, for the export and for readers of older files.
    CONTRACT: Takes one edge row as the export writes it (format 1.0 or 1.1); any ``id`` already in the row is ignored.
    INVARIANTS: Pure: reads only the row and ``EDGE_ID_RULES``; the same row always gives the same id.
    FAILURES: ``ValueError`` naming the type and the field when ``source_id``, ``type``, ``target_id`` or the rule's property is missing, empty, not a string, or contains ``|``.
    AI-CORE-END
    """
    raw_type = row.get("type")
    edge_type = _part(raw_type, str(raw_type), "type")
    source = _part(row.get("source_id"), edge_type, "source_id")
    target = _part(row.get("target_id"), edge_type, "target_id")
    rule = EDGE_ID_RULES.get(edge_type)
    properties = row.get("properties") or {}
    if rule is not None and rule.member is not None:
        target = _part(properties.get(rule.member), edge_type, rule.member)
    parts = [source, edge_type, target]
    if rule is not None and rule.suffix is not None:
        parts.append(_part(properties.get(rule.suffix), edge_type, rule.suffix))
    return EDGE_SEPARATOR.join(parts)
