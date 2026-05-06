# tests/runtime/test_dependency_factory_wiring.py
"""Tests for ``ActionProductMachine.get_tools_box`` dependency wiring."""

from unittest.mock import MagicMock, patch

import pytest

from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.dependency_factory import DependencyFactory
from tests.scenarios.domain_model import FullAction, PingAction
from tests.scenarios.domain_model.services import (
    NotificationServiceResource,
    PaymentServiceResource,
)
from tests.scenarios.domain_model.test_db_manager import OrdersDbManager


def test_get_tools_box_dependency_factory_from_interchange_edges() -> None:
    """get_tools_box builds DependencyFactory from wired @depends interchange edges."""
    machine = ActionProductMachine()
    ctx = MagicMock()
    params = MagicMock()
    action_node = machine.get_action_node_by_id(PingAction)
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

    spy.assert_not_called()
    assert isinstance(box.factory, DependencyFactory)
    assert box.nested_level == 1


def test_full_action_dependency_factory_via_graph_matches_declarations() -> None:
    """Wired interchange @depends yields the same factory mapping as decorator metadata."""
    machine = ActionProductMachine()
    interchange = machine.get_action_node_by_id(FullAction)
    from_graph = interchange.resolved_dependency_infos()
    cls_order = tuple(i.cls for i in from_graph)
    assert PaymentServiceResource in cls_order
    assert NotificationServiceResource in cls_order
    assert OrdersDbManager in cls_order


def test_resolved_dependency_infos_requires_coordinator_when_depends_exist() -> None:
    raw = ActionGraphNode(FullAction)
    assert len(raw.depends) > 0
    with pytest.raises(RuntimeError, match="missing target_node"):
        raw.resolved_dependency_infos()
