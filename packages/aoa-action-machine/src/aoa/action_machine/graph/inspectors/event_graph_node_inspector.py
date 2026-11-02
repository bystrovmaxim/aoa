# packages/aoa-action-machine/src/aoa/action_machine/graph/inspectors/event_graph_node_inspector.py
"""
EventGraphNodeInspector — graph-node contributor for declared ``BaseEvent`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An event enters the graph when something declares it: a domain's ``events`` or a method's
``@emits``. A class nobody names stays out, so a service in the first mode has no event nodes
however many event classes are loaded. An event named many times is still one class on this
axis, so it gets one node.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseDomain.events ─┐
                       ├──► declared events ──► each loaded BaseEvent subclass among them
    BaseAction @emits ─┘                                  │
                                                          v
                                                   EventGraphNode(cls)
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.graph.nodes.event_graph_node import EventGraphNode
from aoa.action_machine.graph.validators.emits_vocabulary_validator import declared_emits
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_event import BaseEvent


class EventGraphNodeInspector(BaseGraphNodeInspector[BaseEvent]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``EventGraphNode`` rows for the events a model declares.
    CONTRACT: Root axis ``BaseEvent``; one node per visited subtype named by some ``events`` or ``@emits`` of a class in the graph.
    AI-CORE-END
    """

    @cached_property
    def _declared(self) -> frozenset[type[Any]]:
        """Every event named by a domain or an action of the graph."""
        declared: set[type[Any]] = set()
        for domain in self._all_descendant_types(BaseDomain):
            if not excluded_from_graph_model(domain):
                declared.update(getattr(domain, "events", ()))
        for action in self._all_descendant_types(BaseAction):
            if not excluded_from_graph_model(action):
                for _method_name, events in declared_emits(action):
                    declared.update(events)
        return frozenset(declared)

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return EventGraphNode(cls) if cls in self._declared else None
