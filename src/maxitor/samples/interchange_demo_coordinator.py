# src/maxitor/samples/interchange_demo_coordinator.py
"""
Interchange coordinator for HTML demos — one graph build for all visualizers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ERD (:mod:`maxitor.visualizer.erd_visualizer`) and the interchange graph visualizer
(:mod:`maxitor.visualizer.graph_visualizer`) both consume a built
:class:`~graph.node_graph_coordinator.NodeGraphCoordinator`. This module is the single
construction path for demos so both exports see identical topology after sample registration.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Call :func:`import_sample_registration_modules` then
:func:`build_registered_interchange_coordinator`. Production coordinator is attempted first;
:class:`~graph.debug_node_graph_coordinator.DebugNodeGraphCoordinator` is used when sample
graphs violate DAG rules (cycles).
"""

from __future__ import annotations

import importlib

from graph.create_node_graph_coordinator import (
    all_axis_graph_node_inspectors,
    create_node_graph_coordinator,
)
from graph.debug_node_graph_coordinator import DebugNodeGraphCoordinator
from graph.exceptions import InvalidGraphError
from graph.node_graph_coordinator import NodeGraphCoordinator


def import_sample_registration_modules() -> None:
    """Import same modules as ``maxitor.samples.build`` for registration side effects."""
    from maxitor.samples.build import _MODULES

    for name in _MODULES:
        importlib.import_module(name)


def build_registered_interchange_coordinator() -> NodeGraphCoordinator:
    """
    Build interchange graph after intents are registered.

    AI-CORE-BEGIN
    CONTRACT: Mirrors production ``create_node_graph_coordinator()`` when DAG-valid; falls back to
        ``DebugNodeGraphCoordinator`` plus ``build(all_axis_graph_node_inspectors())`` otherwise.
    INVARIANTS: Caller must register samples via :func:`import_sample_registration_modules` first.
    AI-CORE-END
    """
    try:
        return create_node_graph_coordinator()
    except InvalidGraphError:
        coord = DebugNodeGraphCoordinator()
        coord.build(all_axis_graph_node_inspectors())
        return coord
