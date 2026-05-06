# src/maxitor/visualizer/erd_visualizer/erd_graph_data.py
"""
Pure data layer for ERD-style graphs — no HTML, no G6.

Builds ``nodes`` / ``edges`` records expected by :mod:`erd_html` (generic ``data`` bags
for the properties panel).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ErdEntitySpec:
    """One ERD entity column set (identifier + human label + optional attributes dict)."""

    id: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErdEdgeSpec:
    """Directed association between two entities (for layout and edge label)."""

    id: str
    source: str
    target: str
    label: str = ""


@dataclass
class ErdGraphPayload:
    """Container for typed ERD specs before conversion to G6-style dicts."""

    entities: tuple[ErdEntitySpec, ...]
    relationships: tuple[ErdEdgeSpec, ...]


def erd_payload_to_g6_records(payload: ErdGraphPayload) -> dict[str, list[dict[str, Any]]]:
    """
    Produce ``{\"nodes\": [...], \"edges\": [...]}`` with string ids compatible with G6.

    Each node carries ``data.label`` plus ``data.payload_panel`` (string values) for
    the inspector panel; visuals are handled entirely in JavaScript (not here).
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    widths: dict[str, float] = {}
    px_per_char = 7.8
    min_w = 88.0
    pad_x = 32.0
    row_h = 18.0
    header_h = 36.0

    def _estimate_width(ent: ErdEntitySpec) -> float:
        title_w = len(ent.label) * px_per_char
        attrs_w = max((len(f"{k}: {v}") for k, v in ent.attributes.items()), default=0) * px_per_char * 0.85
        w = max(min_w, pad_x + max(title_w, attrs_w))
        return float(min(280.0, w))

    def _estimate_height(ent: ErdEntitySpec) -> float:
        body = header_h + max(1, len(ent.attributes)) * row_h + 14.0
        return float(min(320.0, body))

    for ent in payload.entities:
        widths[ent.id] = _estimate_width(ent)

    for ent in payload.entities:
        w = widths[ent.id]
        h = _estimate_height(ent)
        attrs_block = dict(ent.attributes)
        payload_panel = {
            "kind": "entity",
            "id": ent.id,
            "label": ent.label,
            "attributes": attrs_block if attrs_block else {},
        }
        nodes.append({
            "id": ent.id,
            "data": {
                "label": ent.label,
                "subtitle": "",
                "node_type": "entity",
                "fill": "#e8eef7",
                "stroke": "#334155",
                "width": w,
                "height": h,
                "payload_panel": {k: _serialize_panel_value(v) for k, v in payload_panel.items()},
            },
        })

    for rel in payload.relationships:
        edges.append({
            "id": rel.id,
            "source": rel.source,
            "target": rel.target,
            "data": {
                "label": rel.label,
                "payload_panel": {
                    "kind": "relationship",
                    "id": rel.id,
                    "source": rel.source,
                    "target": rel.target,
                    "label": rel.label,
                },
            },
        })

    return {"nodes": nodes, "edges": edges}


def _serialize_panel_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in sorted(value.items())]
        return "\n".join(parts) if parts else ""
    return str(value)


def build_demo_erd_payload() -> ErdGraphPayload:
    """Small sample diagram (customer / order / line) for smoke runs and ``__main__``."""
    return ErdGraphPayload(
        entities=(
            ErdEntitySpec(
                id="entity.customer",
                label="Customer",
                attributes={"email": "string", "status": "enum"},
            ),
            ErdEntitySpec(
                id="entity.order",
                label="Order",
                attributes={"placed_at": "datetime", "total": "decimal"},
            ),
            ErdEntitySpec(
                id="entity.order_line",
                label="OrderLine",
                attributes={"sku": "string", "qty": "int"},
            ),
        ),
        relationships=(
            ErdEdgeSpec(
                id="rel.cust_orders",
                source="entity.customer",
                target="entity.order",
                label="1 — * places",
            ),
            ErdEdgeSpec(
                id="rel.order_lines",
                source="entity.order",
                target="entity.order_line",
                label="1 — * contains",
            ),
        ),
    )
