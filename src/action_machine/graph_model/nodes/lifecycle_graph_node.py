# src/action_machine/graph_model/nodes/lifecycle_graph_node.py
"""
LifeCycleGraphNode — interchange vertex for one ``Lifecycle``-typed field on a host class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one
declared lifecycle field on a host type (typically an ``@entity`` class).
``node_id`` is ``<host_qualname>:lifecycle:<field_name>``; ``node_obj`` is a
frozen :class:`LifeCycleGraphPayload` with host class, trimmed field key, and
caller-supplied lifecycle subtype class.

Template transitions are modeled on companion :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode`
rows (:class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge`):
each companion :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` lists its outgoing arcs in :meth:`~graph.base_graph_node.BaseGraphNode.get_all_edges`.
The parent lifecycle row exposes the same instances in :attr:`~LifeCycleGraphNode.states` and :meth:`~LifeCycleGraphNode.get_all_edges`
as composition links from lifecycle to its status transition graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    :class:`LifeCycleGraphNode`  (this row; ``node_id`` … ``:lifecycle:`` …)
              │
              ├─ :meth:`LifeCycleGraphNode.get_all_edges` / :attr:`~LifeCycleGraphNode.states` → lifecycle composition view of status transitions
              ├─ :attr:`~LifeCycleGraphNode.states` / :meth:`transition_edges` → flattened :class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge`
              ├─ :meth:`LifeCycleGraphNode.state_companion_nodes` / :meth:`~graph.base_graph_node.BaseGraphNode.get_companion_nodes` → companion state vertices
              └─ Companion :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows emit ``lifecycle_transition`` via :meth:`~graph.base_graph_node.BaseGraphNode.get_all_edges`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from action_machine.domain.lifecycle import Lifecycle
from action_machine.graph_model.edges.state_graph_edge import StateGraphEdge
from action_machine.graph_model.nodes.state_graph_node import StateGraphNode
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TLifecycle = TypeVar("TLifecycle", bound=Lifecycle)


@dataclass(frozen=True)
class LifeCycleGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` on a lifecycle interchange row."""

    host_cls: type[Any]
    field_name: str
    lifecycle_class: type[Lifecycle]


@dataclass(init=False, frozen=True)
class LifeCycleGraphNode(BaseGraphNode[LifeCycleGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange vertex for one lifecycle-declared slot on ``host_cls``; **child interchange graph** is carried by companions of type :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode`.
    CONTRACT: ``node_id`` is ``full_qualname(host_cls) + ':lifecycle:' + field_name.strip()``; ``label`` trimmed field key; ``lifecycle_class`` supplied by caller; ``properties`` empty on construction; ``node_obj`` is :class:`LifeCycleGraphPayload`. Canonical state vertices: :meth:`state_companion_nodes`; their ``node_id`` is ``<this.node_id>:<state_key>`` (same root as :attr:`~action_machine.graph_model.nodes.state_graph_node.StateGraphPayload.lifecycle_graph_node_id` on each companion's ``node_obj``).
    TRANSITION ROWS: :attr:`states`, :meth:`transition_edges`, and :meth:`get_all_edges` expose the same :class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge` instances held on companion :class:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode` rows in :attr:`~action_machine.graph_model.nodes.state_graph_node.StateGraphNode.lifecycle_transitions`.
    INVARIANTS: Frozen; companion-sourced outgoing edges are allowed because transition ``source_node_id`` points at child ``StateGraphNode`` ids under this lifecycle namespace; :meth:`state_companion_nodes` recovers source vertices from :attr:`states` and synthesizes sink-only template states.
    FAILURES: :exc:`ValueError` when ``field_name`` is blank after strip.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "lifecycle"
    states: list[StateGraphEdge] = field(init=False)

    def allows_companion_sourced_outgoing_edges(self) -> bool:
        return True

    def __init__(
        self,
        host_cls: type[Any],
        field_name: str,
        lifecycle_cls: type[TLifecycle],
    ) -> None:
        needle = field_name.strip()
        if not needle:
            raise ValueError("LifeCycleGraphNode requires a non-empty field_name")

        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(host_cls)}:lifecycle:{needle}",
            node_type=LifeCycleGraphNode.NODE_TYPE,
            label=needle,
            node_obj=LifeCycleGraphPayload(
                host_cls=host_cls,
                field_name=needle,
                lifecycle_class=lifecycle_cls,
            ),
        )
        verts = LifeCycleGraphNode._materialize_state_vertices(lifecycle_cls, self.node_id)
        object.__setattr__(self, "states", [e for v in verts for e in v.lifecycle_transitions])

    @staticmethod
    def _materialize_state_vertices(
        lifecycle_cls: type[TLifecycle],
        lifecycle_node_id: str,
    ) -> tuple[StateGraphNode, ...]:
        tpl = lifecycle_cls._get_template()
        if tpl is None:
            return ()

        keys: set[str] = set()
        for from_key, state_info in tpl.get_states().items():
            keys.add(from_key)
            keys.update(state_info.transitions)
        sorted_keys = sorted(keys)
        return tuple(StateGraphNode(lifecycle_cls, sk, lifecycle_node_id) for sk in sorted_keys)

    def state_companion_nodes(self) -> list[StateGraphNode]:
        """Return every template state interchange row: edges in :attr:`states` reuse their sources; pure sinks are synthesized once here."""
        tpl = self.node_obj.lifecycle_class._get_template()
        if tpl is None:
            return []

        lc_cls = self.node_obj.lifecycle_class
        nid = self.node_id
        keys: set[str] = set()
        for from_key, state_info in tpl.get_states().items():
            keys.add(from_key)
            keys.update(state_info.transitions)

        sorted_keys = sorted(keys)
        by_vertex_id: dict[str, StateGraphNode] = {}
        for edge in self.states:
            src = edge.source_node
            if isinstance(src, StateGraphNode):
                by_vertex_id[src.node_id] = src

        out: list[StateGraphNode] = []
        for sk in sorted_keys:
            vid = f"{nid}:{sk}"
            vtx = by_vertex_id.get(vid)
            if vtx is None:
                vtx = StateGraphNode(lc_cls, sk, nid)
            out.append(vtx)
        return out

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return cast("list[BaseGraphNode[Any]]", self.state_companion_nodes())

    def transition_edges(self) -> list[StateGraphEdge]:
        """Same instances as :attr:`states` (composition arcs; coordinator hydrates ``target_node`` when graph is assembled)."""
        return [*self.states]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Lifecycle composition view over status-transition edges."""
        return [*self.states]
