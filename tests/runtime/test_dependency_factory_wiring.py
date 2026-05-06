# tests/runtime/test_dependency_factory_wiring.py
"""Tests for ``ActionProductMachine.get_tools_box`` dependency wiring."""

from unittest.mock import MagicMock, patch

from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.dependency_factory import DependencyFactory
from tests.scenarios.domain_model import PingAction


def test_get_tools_box_resolves_via_depends_intent_resolver() -> None:
    """get_tools_box builds DependencyFactory from DependsIntentResolver for action_cls."""
    machine = ActionProductMachine()
    ctx = MagicMock()
    params = MagicMock()
    action_node = ActionGraphNode(PingAction)
    with patch.object(
        DependsIntentResolver,
        "resolve_dependency_infos",
        wraps=DependsIntentResolver.resolve_dependency_infos,
    ) as spy:
        box = machine.get_tools_box(
            context=ctx,
            action_cls=PingAction,
            action_node=action_node,
            params=params,
            resources=None,
            nested_level=1,
            rollup=False,
        )

    spy.assert_called_once_with(PingAction)
    assert isinstance(box.factory, DependencyFactory)
    assert box.nested_level == 1
