# packages/aoa-action-machine/src/aoa/action_machine/interchange/__init__.py
"""
Interchange — documentation anchor for typed graph nodes and edges.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Interchange graphs use ``node_type`` strings on frozen ``BaseGraphNode`` subclasses
and typed ``BaseGraphEdge`` rows emitted by coordinators and inspectors.
Canonical literals live on graph-node classes (for example
:class:`~aoa.action_machine.graph_model.nodes.application_graph_node.ApplicationGraphNode`
and :class:`~aoa.action_machine.graph_model.nodes.domain_graph_node.DomainGraphNode`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    inspectors + graph node / edge classes ──► ``NODE_TYPE`` literals + edges ──► viz / MCP

"""
