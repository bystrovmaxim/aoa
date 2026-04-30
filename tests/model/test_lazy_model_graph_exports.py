# tests/model/test_lazy_model_graph_exports.py
"""
Lazy public exports on ``action_machine.model``, ``model.graph_model``, and ``inspectors``.
"""

from __future__ import annotations

import pytest

import action_machine.model as model_pkg
import action_machine.model.graph_model as graph_model_pkg
from action_machine.model.graph_model.inspectors.action_graph_node_inspector import (
    ActionGraphNodeInspector,
)
from tests.scenarios.domain_model.child_action import ChildAction


def test_model_lazy_action_graph_node_exports() -> None:
    assert model_pkg.ActionGraphNode.__name__ == "ActionGraphNode"
    assert model_pkg.ActionGraphNodeInspector.__name__ == "ActionGraphNodeInspector"


def test_model_getattr_unknown_raises() -> None:
    name = "NotARealModelExport987"
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(model_pkg, name)


def test_graph_model_lazy_getattr_exports_every_all_name() -> None:
    for name in graph_model_pkg.__all__:
        getattr(graph_model_pkg, name)


def test_graph_model_getattr_unknown_raises() -> None:
    name = "NotARealGraphModelExport987"
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(graph_model_pkg, name)


def test_graph_model_dir_lists_public_names() -> None:
    assert "ResultGraphNode" in graph_model_pkg.__dir__()


def test_graph_model_inspectors_lazy_exports() -> None:
    import action_machine.model.graph_model.inspectors as inspectors_pkg

    for name in inspectors_pkg.__all__:
        getattr(inspectors_pkg, name)
    assert "ParamsGraphNodeInspector" in inspectors_pkg.__dir__()


def test_graph_model_inspectors_getattr_unknown_raises() -> None:
    import action_machine.model.graph_model.inspectors as inspectors_pkg

    bad = "NotARealGraphModelInspector884"
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(inspectors_pkg, bad)


def test_action_graph_node_inspector_builds_vertex_for_concrete_action() -> None:
    inspector = ActionGraphNodeInspector()
    vertex = inspector._get_node(ChildAction)  # pylint: disable=protected-access
    assert vertex is not None
    assert vertex.node_obj is ChildAction
