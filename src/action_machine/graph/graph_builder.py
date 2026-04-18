# src/action_machine/graph/graph_builder.py
"""
Interchange construction: :class:`GraphBuilder` and module-level helpers.

- **Synthetic bundle** — ``vertices`` / ``edges`` JSON rows (tests, fixtures).
- **Facet payloads** — ``FacetPayload`` sequence from inspectors / coordinator collect;
  vertex ``id`` equals ``node_name`` (inspectors emit globally unique names; dependent facets
  use ``host:segment``); edges come from payload ``edges`` with a small facet ``edge_type``
  → interchange projection table; **no** automatic §5.3 reverse pairs (forward edges only).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from action_machine.graph.constants import INTERNAL_EDGE_TYPES, OWNERSHIP_EDGE_TYPES
from action_machine.graph.model import GraphEdge, GraphVertex
from action_machine.graph.payload import FacetPayload

_VERTEX_KEYS: frozenset[str] = frozenset(GraphVertex.__dataclass_fields__)
_EDGE_KEYS: frozenset[str] = frozenset(GraphEdge.__dataclass_fields__)

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


def _assert_unique_vertex_ids(rows: list[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for row in rows:
        vid = str(row["id"])
        if vid in seen:
            msg = f"duplicate vertex id {vid!r}"
            raise ValueError(msg)
        seen.add(vid)


def _vertex_from_row(row: Mapping[str, Any]) -> GraphVertex:
    missing = _VERTEX_KEYS - row.keys()
    if missing:
        msg = f"vertex row missing keys {sorted(missing)!r}"
        raise KeyError(msg)
    extra = set(row) - _VERTEX_KEYS
    if extra:
        msg = f"vertex row has unknown keys {sorted(extra)!r}"
        raise ValueError(msg)
    cr = row["class_ref"]
    if cr is not None and not isinstance(cr, type):
        msg = "vertex class_ref must be null or a type object"
        raise TypeError(msg)
    return GraphVertex(
        id=str(row["id"]),
        node_type=str(row["node_type"]),
        stereotype=str(row["stereotype"]),
        label=str(row["label"]),
        class_ref=cr,
        properties=dict(row["properties"]),
    )


def _edge_from_row(row: Mapping[str, Any]) -> GraphEdge:
    missing = _EDGE_KEYS - row.keys()
    if missing:
        msg = f"edge row missing keys {sorted(missing)!r}"
        raise KeyError(msg)
    extra = set(row) - _EDGE_KEYS
    if extra:
        msg = f"edge row has unknown keys {sorted(extra)!r}"
        raise ValueError(msg)
    return GraphEdge(
        source_id=str(row["source_id"]),
        target_id=str(row["target_id"]),
        edge_type=str(row["edge_type"]),
        stereotype=str(row["stereotype"]),
        category=str(row["category"]),
        is_dag=bool(row["is_dag"]),
        attributes=dict(row["attributes"]),
    )


def build_from_synthetic_bundle(inp: Mapping[str, Any]) -> tuple[list[GraphVertex], list[GraphEdge]]:
    """
    Deserialize ``inp["vertices"]`` and ``inp["edges"]`` into interchange dataclasses.

    Raises:
        KeyError: missing ``vertices`` / ``edges`` or a required field on a row.
        ValueError: duplicate vertex ``id``, unknown edge endpoint, or unknown keys on a row.
        TypeError: ``vertices``/``edges`` not lists, or ``class_ref`` not null/type.
    """
    vertices_raw = inp["vertices"]
    edges_raw = inp["edges"]
    if not isinstance(vertices_raw, list) or not isinstance(edges_raw, list):
        msg = "vertices and edges must be lists"
        raise TypeError(msg)

    _assert_unique_vertex_ids(vertices_raw)
    vertices = [_vertex_from_row(r) for r in vertices_raw]
    vertex_ids = {v.id for v in vertices}

    edges: list[GraphEdge] = []
    for r in edges_raw:
        e = _edge_from_row(r)
        if e.source_id not in vertex_ids:
            msg = f"edge references unknown source_id {e.source_id!r}"
            raise ValueError(msg)
        if e.target_id not in vertex_ids:
            msg = f"edge references unknown target_id {e.target_id!r}"
            raise ValueError(msg)
        edges.append(e)

    return vertices, edges


def _interchange_vertex_id(payload: FacetPayload) -> str:
    """Interchange vertex id — identical to inspector ``node_name`` (globally unique)."""
    return payload.node_name


def _tail_name(qualname: str) -> str:
    return qualname.rsplit(".", maxsplit=1)[-1]


def _facet_vertex_label(p: FacetPayload) -> str:
    """
    Short labels for lifecycle facets: state nodes use the two-part id (e.g. ``SalesOrderLifecycle:new``),
    lifecycle field nodes use the model field name (e.g. ``lifecycle``).
    """
    meta = dict(p.node_meta)
    if str(p.node_type).startswith("lifecycle_state"):
        return p.node_name
    if p.node_type == "lifecycle" and "field_name" in meta:
        return str(meta["field_name"])
    return _tail_name(p.node_name)


def _from_facet_payloads(
    payloads: tuple[FacetPayload, ...],
) -> tuple[list[GraphVertex], list[GraphEdge]]:
    vertices_by_id: dict[str, GraphVertex] = {}

    for p in payloads:
        vid = _interchange_vertex_id(p)
        if vid in vertices_by_id:
            msg = f"duplicate vertex id {vid!r}"
            raise ValueError(msg)
        vertices_by_id[vid] = GraphVertex(
            id=vid,
            node_type=p.node_type,
            stereotype="",
            label=_facet_vertex_label(p),
            class_ref=None,
            properties={},
        )

    edges: list[GraphEdge] = []
    seen_forward: set[tuple[str, str, str]] = set()

    for p in payloads:
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
                attributes=attrs,
            )
            edges.append(forward)

    vertices = list(vertices_by_id.values())
    return vertices, edges


def build_interchange_from_facet_payloads(
    payloads: Sequence[FacetPayload],
) -> tuple[list[GraphVertex], list[GraphEdge]]:
    """
    Build interchange vertex/edge lists from facet payload rows.

    Raises:
        ValueError: unknown facet ``edge_type``, unknown edge endpoint id, or duplicate vertex id.
    """
    return _from_facet_payloads(tuple(payloads))


class GraphBuilder:
    """Build interchange lists from a synthetic JSON bundle or from facet payloads."""

    @classmethod
    def build(
        cls,
        *,
        synthetic_bundle: Mapping[str, Any],
    ) -> tuple[list[GraphVertex], list[GraphEdge]]:
        """Deserialize a synthetic ``vertices`` / ``edges`` bundle."""
        return build_from_synthetic_bundle(synthetic_bundle)

    @classmethod
    def build_from_facet_payloads(
        cls,
        *,
        facet_payloads: Sequence[FacetPayload],
    ) -> tuple[list[GraphVertex], list[GraphEdge]]:
        """Same as :func:`build_interchange_from_facet_payloads`."""
        return build_interchange_from_facet_payloads(facet_payloads)
