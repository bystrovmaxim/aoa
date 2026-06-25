# tests/action_machine/smoke/test_lazy_model_graph_exports.py
"""Public model exports and direct graph-model leaf imports."""

from __future__ import annotations

import aoa.action_machine.graph as graph_pkg
import aoa.action_machine.graph.inspectors as inspectors_pkg
import aoa.action_machine.model as model_pkg
from aoa.action_machine.graph.inspectors.action_graph_node_inspector import ActionGraphNodeInspector
from aoa.action_machine.graph.inspectors.params_graph_node_inspector import ParamsGraphNodeInspector
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.nodes.result_graph_node import ResultGraphNode

from ...support.domain_model.child_action import ChildAction


def test_model_package_exports_core_contracts_only() -> None:
    assert model_pkg.BaseAction.__name__ == "BaseAction"
    assert model_pkg.BaseParams.__name__ == "BaseParams"
    assert model_pkg.BaseResult.__name__ == "BaseResult"
    assert not hasattr(model_pkg, "ActionGraphNode")


def test_graph_package_reexports_core_symbols() -> None:
    assert graph_pkg.BaseGraphNode.__name__ == "BaseGraphNode"
    assert not hasattr(graph_pkg, "ResultGraphNode")
    assert not hasattr(graph_pkg, "create_node_graph_coordinator")


def test_graph_factory_leaf_import_resolves() -> None:
    from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator

    assert create_node_graph_coordinator.__name__ == "create_node_graph_coordinator"


def test_graph_leaf_imports_resolve() -> None:
    assert ActionGraphNode.__name__ == "ActionGraphNode"
    assert ResultGraphNode.__name__ == "ResultGraphNode"


def test_graph_inspector_leaf_imports_resolve() -> None:
    assert inspectors_pkg.__all__ == []
    assert ActionGraphNodeInspector.__name__ == "ActionGraphNodeInspector"
    assert ParamsGraphNodeInspector.__name__ == "ParamsGraphNodeInspector"


def test_action_graph_node_inspector_builds_graph_node_for_concrete_action() -> None:
    inspector = ActionGraphNodeInspector()
    graph_node = inspector._get_node(ChildAction)  # pylint: disable=protected-access
    assert graph_node is not None
    assert graph_node.node_obj is ChildAction
