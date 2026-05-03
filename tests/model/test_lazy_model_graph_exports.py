# tests/model/test_lazy_model_graph_exports.py
"""Public model exports and direct graph-model leaf imports."""

from __future__ import annotations

import action_machine.graph_model as graph_model_pkg
import action_machine.graph_model.inspectors as inspectors_pkg
import action_machine.model as model_pkg
from action_machine.graph_model.inspectors.action_graph_node_inspector import (
    ActionGraphNodeInspector,
)
from action_machine.graph_model.inspectors.params_graph_node_inspector import (
    ParamsGraphNodeInspector,
)
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
from tests.scenarios.domain_model.child_action import ChildAction


def test_model_package_exports_core_contracts_only() -> None:
    assert model_pkg.BaseAction.__name__ == "BaseAction"
    assert model_pkg.BaseParams.__name__ == "BaseParams"
    assert model_pkg.BaseResult.__name__ == "BaseResult"
    assert not hasattr(model_pkg, "ActionGraphNode")


def test_graph_model_package_does_not_reexport_leaf_symbols() -> None:
    assert graph_model_pkg.__all__ == []
    assert not hasattr(graph_model_pkg, "ResultGraphNode")


def test_graph_model_leaf_imports_resolve() -> None:
    assert ActionGraphNode.__name__ == "ActionGraphNode"
    assert ResultGraphNode.__name__ == "ResultGraphNode"


def test_graph_model_inspector_leaf_imports_resolve() -> None:
    assert inspectors_pkg.__all__ == []
    assert ActionGraphNodeInspector.__name__ == "ActionGraphNodeInspector"
    assert ParamsGraphNodeInspector.__name__ == "ParamsGraphNodeInspector"


def test_action_graph_node_inspector_builds_vertex_for_concrete_action() -> None:
    inspector = ActionGraphNodeInspector()
    vertex = inspector._get_node(ChildAction)  # pylint: disable=protected-access
    assert vertex is not None
    assert vertex.node_obj is ChildAction
