# tests/application/test_application_graph_node.py
"""Unit tests for :class:`~action_machine.graph_model.nodes.application_graph_node.ApplicationGraphNode`."""

from __future__ import annotations

from action_machine.application import Application
from action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from action_machine.system_core.type_introspection import TypeIntrospection


def test_application_graph_node_wraps_marker_class() -> None:
    """node_id uses full qualname; properties read class attributes."""
    n = ApplicationGraphNode(Application)
    assert n.node_type == ApplicationGraphNode.NODE_TYPE == "Application"
    assert n.label == "Application"
    assert n.node_id == TypeIntrospection.full_qualname(Application)
    assert n.properties["name"] == Application.name
    assert n.properties["description"] == Application.description
    assert n.node_obj is Application


def test_application_graph_node_accepts_strict_subclass() -> None:
    class ProjectApplication(Application):
        name = "project_x"
        description = "Subclass still bound to Application."

    n = ApplicationGraphNode(ProjectApplication)
    assert n.label == "ProjectApplication"
    assert n.properties["name"] == "project_x"
