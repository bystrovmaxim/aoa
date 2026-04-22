# src/maxitor/viz2/visualizer_icons.py
"""
Lucide icon markup (inner SVG children only) per ``node_type``.

Icons are from `lucide-static` (ISC, https://github.com/lucide-icons/lucide).
Rendered as white strokes on the colored node disk in :mod:`maxitor.viz2.interchange_graph_visualizer`.

Interchange axis kinds share ``NODE_TYPE`` from :class:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode`,
:class:`~action_machine.model.graph_model.checker_graph_node.CheckerGraphNode`,
:class:`~action_machine.model.graph_model.params_graph_node.ParamsGraphNode`, :class:`~action_machine.model.graph_model.result_graph_node.ResultGraphNode`,
:class:`~action_machine.model.graph_model.field_graph_node.FieldGraphNode`, :class:`~action_machine.model.graph_model.property_field_graph_node.PropertyFieldGraphNode`,
:class:`~action_machine.domain.graph_model.entity_graph_node.EntityGraphNode`, :class:`~action_machine.domain.graph_model.domain_graph_node.DomainGraphNode`,
and :class:`~action_machine.auth.graph_model.role_graph_node.RoleGraphNode`. Other keys are facet-only strings (no graph-node class).
"""

from __future__ import annotations

from urllib.parse import quote

from action_machine.auth.graph_model.role_graph_node import RoleGraphNode
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.domain.graph_model.entity_graph_node import EntityGraphNode
from action_machine.legacy.interchange_vertex_labels import (
    APPLICATION_VERTEX_TYPE,
    SERVICE_VERTEX_TYPE,
)
from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from action_machine.model.graph_model.compensator_graph_node import CompensatorGraphNode
from action_machine.model.graph_model.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.model.graph_model.field_graph_node import FieldGraphNode
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.property_field_graph_node import PropertyFieldGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from action_machine.model.graph_model.result_graph_node import ResultGraphNode
from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode

# ``ErrorHandler``: amber disk + darker amber glyph (single hue family; avoids neon yellow / fire-engine red).
_ERROR_HANDLER_INNER_STROKE: str = "#B45309"

# Shared Lucide ``braces`` inner SVG for ``Field`` and ``PropertyField`` rows (disk fill differs per ``node_type``).
_LUCIDE_FIELD_OR_PROPERTY_INNER: str = (
    '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1" /> '
    '<path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1" />'
)

# fmt: off
# Inner elements only (no <svg> wrapper), spaces preserved for valid XML.
VERTEX_TYPE_LUCIDE_INNER_SVG: dict[str, str] = {
    APPLICATION_VERTEX_TYPE: (
        '<rect width="7" height="9" x="3" y="3" rx="1" /> '
        '<rect width="7" height="5" x="14" y="3" rx="1" /> '
        '<rect width="7" height="9" x="14" y="12" rx="1" /> '
        '<rect width="7" height="5" x="3" y="16" rx="1" />'
    ),
    ActionGraphNode.NODE_TYPE: (
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />'
    ),
    DomainGraphNode.NODE_TYPE: (
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /> '
        '<path d="m3.3 7 8.7 5 8.7-5" /> '
        '<path d="M12 22V12" />'
    ),
    "dependency": (
        '<path d="M12 22v-5" /> '
        '<path d="M9 8V2" /> '
        '<path d="M15 8V2" /> '
        '<path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />'
    ),
    "connection": (
        '<path d="M9 17H7A5 5 0 0 1 7 7h2" /> '
        '<path d="M15 7h2a5 5 0 1 1 0 10h-2" /> '
        '<line x1="8" x2="16" y1="12" y2="12" />'
    ),
    # Lucide ``arrow-down-wide-narrow`` / ``arrow-up-narrow-wide`` (same stroke grammar; orange fill in UI).
    RegularAspectGraphNode.NODE_TYPE: (
        '<path d="m3 16 4 4 4-4" /> '
        '<path d="M7 20V4" /> '
        '<path d="M11 4h10" /> '
        '<path d="M11 8h7" /> '
        '<path d="M11 12h4" />'
    ),
    SummaryAspectGraphNode.NODE_TYPE: (
        '<path d="m3 8 4-4 4 4" /> '
        '<path d="M7 4v16" /> '
        '<path d="M11 12h4" /> '
        '<path d="M11 16h7" /> '
        '<path d="M11 20h10" />'
    ),
    CheckerGraphNode.NODE_TYPE: (
        '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z" /> '
        '<path d="m9 12 2 2 4-4" />'
    ),
    CompensatorGraphNode.NODE_TYPE: (
        '<path d="M9 14 4 9l5-5" /> '
        '<path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11" />'
    ),
    ErrorHandlerGraphNode.NODE_TYPE: (
        f'<path fill="none" stroke="{_ERROR_HANDLER_INNER_STROKE}" d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /> '
        f'<path fill="none" stroke="{_ERROR_HANDLER_INNER_STROKE}" d="M12 9v4" /> '
        f'<path fill="none" stroke="{_ERROR_HANDLER_INNER_STROKE}" d="M12 17h.01" />'
    ),
    EntityGraphNode.NODE_TYPE: (
        '<ellipse cx="12" cy="5" rx="9" ry="3" /> '
        '<path d="M3 5V19A9 3 0 0 0 21 19V5" /> '
        '<path d="M3 12A9 3 0 0 0 21 12" />'
    ),
    "lifecycle": (
        '<circle cx="18" cy="6" r="3" /> '
        '<circle cx="6" cy="18" r="3" /> '
        '<path d="M18 9v1a4 4 0 0 1-4 4H9a4 4 0 0 0-4 4v1" />'
    ),
    # Lifecycle states: shared ring motif, varied inner mark (entry / in-flight / done).
    "lifecycle_state_initial": (
        '<circle cx="12" cy="12" r="9" /> '
        '<circle cx="12" cy="12" r="3" fill="#ffffff" stroke="none" />'
    ),
    "lifecycle_state_intermediate": (
        '<circle cx="12" cy="12" r="9" /> '
        '<circle cx="12" cy="12" r="4" />'
    ),
    "lifecycle_state_final": (
        '<circle cx="12" cy="12" r="9" /> '
        '<path d="m8 12 2 2 4-4" />'
    ),
    # Legacy interchange rows (alias to intermediate glyph).
    "lifecycle_state": (
        '<circle cx="12" cy="12" r="9" /> '
        '<circle cx="12" cy="12" r="4" />'
    ),
    "resource_manager": (
        '<line x1="22" x2="2" y1="12" y2="12" /> '
        '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /> '
        '<line x1="6" x2="6.01" y1="16" y2="16" /> '
        '<line x1="10" x2="10.01" y1="16" y2="16" />'
    ),
    "role_class": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />'
    ),
    "role": (
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /> '
        '<circle cx="12" cy="7" r="4" />'
    ),
    "role_mode": (
        '<line x1="21" x2="14" y1="4" y2="4" /> '
        '<line x1="10" x2="3" y1="4" y2="4" /> '
        '<line x1="21" x2="12" y1="12" y2="12" /> '
        '<line x1="8" x2="3" y1="12" y2="12" /> '
        '<line x1="21" x2="16" y1="20" y2="20" /> '
        '<line x1="12" x2="3" y1="20" y2="20" /> '
        '<line x1="14" x2="14" y1="2" y2="6" /> '
        '<line x1="8" x2="8" y1="10" y2="14" /> '
        '<line x1="16" x2="16" y1="18" y2="22" />'
    ),
    "sensitive_field": (
        '<rect width="18" height="11" x="3" y="11" rx="2" ry="2" /> '
        '<path d="M7 11V7a5 5 0 0 1 10 0v4" />'
    ),
    "described_fields": (
        '<path d="M3 12h.01" /> '
        '<path d="M3 18h.01" /> '
        '<path d="M3 6h.01" /> '
        '<path d="M8 12h13" /> '
        '<path d="M8 18h13" /> '
        '<path d="M8 6h13" />'
    ),
    ParamsGraphNode.NODE_TYPE: (
        '<path d="M17 12H3" /> '
        '<path d="m11 18 6-6-6-6" /> '
        '<path d="M21 5v14" />'
    ),
    ResultGraphNode.NODE_TYPE: (
        '<path d="M3 19V5" /> '
        '<path d="m13 6-6 6 6 6" /> '
        '<path d="M7 12h14" />'
    ),
    FieldGraphNode.NODE_TYPE: _LUCIDE_FIELD_OR_PROPERTY_INNER,
    PropertyFieldGraphNode.NODE_TYPE: _LUCIDE_FIELD_OR_PROPERTY_INNER,
    "plugin": (
        '<path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z" />'
    ),
    "subscription": (
        '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /> '
        '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /> '
        '<path d="M4 2C2.8 3.7 2 5.7 2 8" /> '
        '<path d="M22 8c0-2.3-.8-4.3-2-6" />'
    ),
    "service": (
        '<path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" /> '
        '<path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" /> '
        '<path d="M12 2v2" /> '
        '<path d="M12 22v-2" /> '
        '<path d="m17 20.66-1-1.73" /> '
        '<path d="M11 10.27 7 3.34" /> '
        '<path d="m20.66 17-1.73-1" /> '
        '<path d="m3.34 7 1.73 1" /> '
        '<path d="M14 12h8" /> '
        '<path d="M2 12h2" /> '
        '<path d="m20.66 7-1.73 1" /> '
        '<path d="m3.34 17 1.73-1" /> '
        '<path d="m17 3.34-1 1.73" /> '
        '<path d="m11 13.73-4 6.93" />'
    ),
    "unknown": (
        '<path d="M12 22v-5" /> '
        '<path d="M9 8V2" /> '
        '<path d="M15 8V2" /> '
        '<path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />'
    ),
}
# fmt: on

VERTEX_TYPE_LUCIDE_INNER_SVG[SERVICE_VERTEX_TYPE] = VERTEX_TYPE_LUCIDE_INNER_SVG[
    "dependency"
]
VERTEX_TYPE_LUCIDE_INNER_SVG[RoleGraphNode.NODE_TYPE] = VERTEX_TYPE_LUCIDE_INNER_SVG["role_class"]

# Scale Lucide paths (native 24×24) about the center so strokes sit inside the disk with margin.
_ICON_INNER_SCALE: float = 0.58
# Keep apparent stroke width ~2 after scaling (stroke scales with transform).
_ICON_STROKE_WIDTH: float = 2.0 / _ICON_INNER_SCALE


def svg_data_uri_for_vertex_icon(fill_hex: str, node_type: str) -> str:
    """Return a data: URL for a 24×24 disk with ``fill_hex``; Lucide strokes are white except ``ErrorHandler`` (amber-on-amber glyph)."""
    # Types not in the map use the same plug / "fork" glyph as ``dependency``.
    inner = VERTEX_TYPE_LUCIDE_INNER_SVG.get(str(node_type).strip()) or VERTEX_TYPE_LUCIDE_INNER_SVG[
        "dependency"
    ]
    s = _ICON_INNER_SCALE
    sw = _ICON_STROKE_WIDTH
    # translate → scale about (12,12) → translate back — icon inset with even padding inside r=11 circle.
    g_open = (
        f'<g transform="translate(12,12) scale({s}) translate(-12,-12)" '
        f'fill="none" stroke="#ffffff" stroke-width="{sw:.4f}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<circle cx="12" cy="12" r="11" fill="{fill_hex}"/>'
        f"{g_open}{inner}</g></svg>"
    )
    return "data:image/svg+xml," + quote(svg)
