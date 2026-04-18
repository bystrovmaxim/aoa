# src/action_machine/graph/model.py
"""
Re-export interchange vertex/edge types (one class per module under :mod:`action_machine.graph`).
"""

from __future__ import annotations

from action_machine.graph.graph_edge import GraphEdge
from action_machine.graph.graph_vertex import GraphVertex

__all__ = ("GraphEdge", "GraphVertex")
