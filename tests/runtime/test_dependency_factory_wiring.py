# tests/runtime/test_dependency_factory_wiring.py
"""Tests for interchange-based ``DependencyFactory`` wiring used with ``ToolsBox``."""

from functools import partial
from unittest.mock import MagicMock, patch

import pytest

from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_state import BaseState
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.dependency_factory import DependencyFactory
from action_machine.runtime.tools_box import ToolsBox
from tests.scenarios.domain_model import FullAction, PingAction
from tests.scenarios.domain_model.services import (
    NotificationServiceResource,
    PaymentServiceResource,
)
from tests.scenarios.domain_model.test_db_manager import OrdersDbManager


def test_tools_box_dependency_factory_from_interchange_edges() -> None:
    """ToolsBox uses DependencyFactory built from wired @depends interchange edges."""
    machine = ActionProductMachine()
    ctx = MagicMock()
    params = MagicMock()
    action_node = machine.get_action_node_by_id(PingAction)
    log = ScopedLogger(
        coordinator=machine._log_coordinator,
        nest_level=1,
        action_name=action_node.node_id,
        aspect_name="",
        context=ctx,
        state=BaseState(),
        params=params,
        domain=action_node.domain.target_node.node_obj,
    )
    with patch.object(
        DependsIntentResolver,
        "resolve_dependency_infos",
        wraps=DependsIntentResolver.resolve_dependency_infos,
    ) as spy:
        box = ToolsBox(
            run_child=partial(
                machine._run_internal,
                context=ctx,
                resources=None,
                nested_level=1,
                rollup=False,
            ),
            resources=None,
            log=log,
            nested_level=1,
            rollup=False,
            factory=DependencyFactory(action_node.resolved_dependency_infos()),
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
