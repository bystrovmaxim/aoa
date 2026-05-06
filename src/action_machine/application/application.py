# src/action_machine/application/application.py
"""
Application — single marker class for interchange ``Application`` vertices.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One logical application root per interchange graph. Metadata is plain class
attributes; :class:`~action_machine.graph_model.inspectors.application_graph_node_inspector.ApplicationGraphNodeInspector`
emits :class:`~action_machine.graph_model.nodes.application_graph_node.ApplicationGraphNode`
for this type (and any strict subclasses if present).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Application  ──>  ApplicationGraphNode(Application)  ──>  coordinator / viz

"""

from __future__ import annotations


class Application:
    """
    AI-CORE-BEGIN
    ROLE: Typed application root marker for interchange ``Application`` vertices.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes for graph properties.
    INVARIANTS: No instances required; used as ``node_obj`` on ``ApplicationGraphNode``.
    AI-CORE-END
    """

    name = "application"
    description = "Logical application root for interchange graphs."
