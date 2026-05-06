# src/action_machine/graph_model/inspectors/role_graph_node_inspector.py
"""
RoleGraphNodeInspector — graph-node contributor for ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks the loaded strict ``BaseRole`` subclass tree and emits one :class:`RoleGraphNode` per
subtype that participates in interchange; classes opt out with
:class:`~graph.exclude_graph_model.exclude_graph_model` (see :meth:`~graph.base_graph_node_inspector.BaseGraphNodeInspector.get_graph_nodes`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole  (axis root — skipped when decorated with ``exclude_graph_model``)
              │
              v
    each visited ``cls``  ->  ``[RoleGraphNode(cls)]`` when the class is a ``BaseRole``
    subtype **and** declares ``@role_mode`` (valid ``_role_mode_info``).

    Classes without ``@role_mode`` are skipped: CPython keeps failed subclasses in
    ``BaseRole.__subclasses__()`` when ``__init_subclass__`` raises (for example,
    invalid ``name`` / ``description`` in role validation tests).
"""

from __future__ import annotations

from typing import Any

from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector

from ..nodes.role_graph_node import RoleGraphNode


class RoleGraphNodeInspector(BaseGraphNodeInspector[BaseRole]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``RoleGraphNode`` rows for visited ``BaseRole`` classes.
    CONTRACT: Root axis ``BaseRole``; emit one node per subclass with valid ``@role_mode`` metadata only.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if not isinstance(cls, type) or not issubclass(cls, BaseRole):
            return None
        info = getattr(cls, "_role_mode_info", None)
        if not isinstance(info, dict) or not isinstance(info.get("mode"), RoleMode):
            return None
        return RoleGraphNode(cls)
