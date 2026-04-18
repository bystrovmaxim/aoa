# src/action_machine/graph/graph_builder.py
"""
Interchange construction: :class:`GraphBuilder` and module-level helpers.

**Facet vertices** — ``FacetVertex`` sequence from inspectors / coordinator collect;
vertex ``id`` equals ``node_name`` (inspectors emit globally unique names; dependent facets
use ``host:segment``); edges come from each vertex's ``edges`` with a small facet ``edge_type``
→ interchange projection table (forward edges only).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from action_machine.graph.constants import INTERNAL_EDGE_TYPES, OWNERSHIP_EDGE_TYPES
from action_machine.graph.facet_vertex import FacetVertex
from action_machine.graph.graph_edge import GraphEdge
from action_machine.graph.graph_vertex import GraphVertex

# facet edge_type (inspectors) → (interchange edge_type, forward stereotype)
_FACET_EDGE_TO_INTERCHANGE: Final[dict[str, tuple[str, str]]] = {
    "belongs_to": ("BELONGS_TO", "Aggregation"),
    "depends": ("DEPENDS_ON", "Dependency"),
    "connection": ("CONNECTS_TO", "Flow"),
    "requires_role": ("ASSIGNED_TO", "Assignment"),
    "has_aspect": ("HAS_ASPECT", "Composition"),
    "checks_aspect": ("CHECKS_ASPECT", "Influence"),
    "uses_params": ("HAS_PARAMS", "Schema"),
    "uses_result": ("HAS_RESULT", "Schema"),
    "has_sensitive_field": ("HAS_SENSITIVE_FIELD", "Composition"),
    "has_error_handler": ("HAS_ERROR_HANDLER", "Composition"),
    "has_compensator": ("HAS_COMPENSATOR", "Composition"),
    "entity_composition_one": ("COMPOSITION_ONE", "Composition"),
    "entity_composition_many": ("COMPOSITION_MANY", "Composition"),
    "entity_aggregation_one": ("AGGREGATION_ONE", "Aggregation"),
    "entity_aggregation_many": ("AGGREGATION_MANY", "Aggregation"),
    "entity_association_one": ("ASSOCIATION_ONE", "Association"),
    "entity_association_many": ("ASSOCIATION_MANY", "Association"),
    "entity_has_lifecycle": ("HAS_LIFECYCLE", "Composition"),
    "lifecycle_contains_state": ("HAS_LIFECYCLE_STATE", "Composition"),
    "lifecycle_initial": ("LIFECYCLE_INITIAL", "Association"),
    "lifecycle_transition": ("LIFECYCLE_TRANSITION", "Flow"),
}


def _interchange_vertex_id(vertex: FacetVertex) -> str:
    """Interchange vertex id — identical to inspector ``node_name`` (globally unique)."""
    return vertex.node_name


def _tail_name(qualname: str) -> str:
    return qualname.rsplit(".", maxsplit=1)[-1]


def _aspect_method_name_from_meta(meta: Mapping[str, Any]) -> str | None:
    """First aspect row ``method_name`` when ``aspects`` metadata is present."""
    raw = meta.get("aspects")
    if not raw:
        return None
    first = raw[0] if isinstance(raw, (list, tuple)) and raw else None
    if first is None:
        return None
    row = dict(first)
    s = str(row.get("method_name", "") or "").strip()
    return s or None


def _facet_vertex_label(p: FacetVertex) -> str:
    """
    Short display label for an interchange vertex.

    Uses only ``node_meta`` shape and a few **structural** ``node_type`` prefixes
    (lifecycle state ids); does not import application facet kind constants.
    """
    meta = dict(p.node_meta)
    nt = str(p.node_type)
    if meta.get("aspects"):
        method = _aspect_method_name_from_meta(meta)
        if method:
            return method
    if meta.get("checker_class") is not None:
        field = str(meta.get("field_name", "") or "").strip()
        if field:
            return field
    method = str(meta.get("method_name", "") or "").strip()
    if method:
        return method
    if nt.startswith("lifecycle_state"):
        return p.node_name
    if nt == "lifecycle" and "field_name" in meta:
        return str(meta["field_name"])
    return _tail_name(p.node_name)


def _from_facet_vertices(
    facet_vertices: tuple[FacetVertex, ...],
) -> tuple[list[GraphVertex], list[GraphEdge]]:
    vertices_by_id: dict[str, GraphVertex] = {}

    for p in facet_vertices:
        vid = _interchange_vertex_id(p)
        if vid in vertices_by_id:
            msg = f"duplicate vertex id {vid!r}"
            raise ValueError(msg)
        vertices_by_id[vid] = GraphVertex(
            id=vid,
            node_type=p.node_type,
            label=_facet_vertex_label(p),
            properties={},
            links=[],
        )

    edges: list[GraphEdge] = []
    seen_forward: set[tuple[str, str, str, tuple[tuple[str, Any], ...]]] = set()

    for p in facet_vertices:
        source_id = _interchange_vertex_id(p)
        for e in p.edges:
            target_id = e.target_name
            row = _FACET_EDGE_TO_INTERCHANGE.get(e.edge_type)
            if row is None:
                msg = f"unknown facet edge_type {e.edge_type!r}"
                raise ValueError(msg)
            interchange_type, forward_st = row
            if source_id not in vertices_by_id:
                msg = f"edge references unknown source_id {source_id!r}"
                raise ValueError(msg)
            if target_id not in vertices_by_id:
                msg = f"edge references unknown target_id {target_id!r}"
                raise ValueError(msg)

            attrs: dict[str, Any] = dict(e.edge_meta) if e.edge_meta else {}
            is_dag = bool(e.is_structural)
            attr_key = tuple(sorted(attrs.items())) if attrs else ()
            dedupe_key = (source_id, target_id, interchange_type, attr_key)
            if dedupe_key in seen_forward:
                continue
            seen_forward.add(dedupe_key)

            if interchange_type in OWNERSHIP_EDGE_TYPES:
                forward_category = "ownership"
            elif interchange_type in INTERNAL_EDGE_TYPES:
                forward_category = "internal"
            else:
                forward_category = "direct"

            forward = GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=interchange_type,
                stereotype=forward_st,
                category=forward_category,
                is_dag=is_dag,
                properties=attrs,
            )
            edges.append(forward)

    vertices = list(vertices_by_id.values())
    return vertices, edges


def build_interchange_from_facet_vertices(
    facet_vertices: Sequence[FacetVertex],
) -> tuple[list[GraphVertex], list[GraphEdge]]:
    """
    Build interchange vertex/edge lists from facet vertex rows.

    Raises:
        ValueError: unknown facet ``edge_type``, unknown edge endpoint id, or duplicate vertex id.
    """
    return _from_facet_vertices(tuple(facet_vertices))


class GraphBuilder:
    """Build interchange lists from facet vertices."""

    @classmethod
    def build_from_facet_vertices(
        cls,
        *,
        facet_vertices: Sequence[FacetVertex],
    ) -> tuple[list[GraphVertex], list[GraphEdge]]:
        """Same as :func:`build_interchange_from_facet_vertices`."""
        return build_interchange_from_facet_vertices(facet_vertices)
