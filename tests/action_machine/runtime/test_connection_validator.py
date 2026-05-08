# tests/runtime/test_connection_validator.py
"""
Unit tests for :class:`~aoa.action_machine.runtime.connection_validator.ConnectionValidator`.

Validates declared ``@connection`` keys against caller-supplied mappings and ``BaseResource`` values.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aoa.action_machine.exceptions import ConnectionValidationError
from aoa.action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.runtime.connection_validator import ConnectionValidator
from tests.action_machine.scenarios.domain_model.child_action import ChildAction
from tests.action_machine.scenarios.domain_model.full_action import FullAction
from tests.action_machine.scenarios.domain_model.test_db_manager import OrdersDbManager


def _action_node(cls: type) -> ActionGraphNode:
    return ActionGraphNode(cls)


def test_validate_accepts_none_or_empty_when_no_connections_declared() -> None:
    validator = ConnectionValidator()
    node = _action_node(ChildAction)
    assert validator.validate(ChildAction(), None, node) == {}
    assert validator.validate(ChildAction(), {}, node) == {}


def test_validate_rejects_connections_when_action_declares_none() -> None:
    validator = ConnectionValidator()
    resource = OrdersDbManager()
    with pytest.raises(ConnectionValidationError, match="does not declare any @connection"):
        validator.validate(ChildAction(), {"db": resource}, _action_node(ChildAction))


def test_validate_rejects_empty_mapping_when_connections_required() -> None:
    validator = ConnectionValidator()
    node = _action_node(FullAction)
    with pytest.raises(ConnectionValidationError, match="no connections were passed"):
        validator.validate(FullAction(), None, node)
    with pytest.raises(ConnectionValidationError, match="no connections were passed"):
        validator.validate(FullAction(), {}, node)


def test_validate_rejects_extra_keys() -> None:
    validator = ConnectionValidator()
    resource = OrdersDbManager()
    with pytest.raises(ConnectionValidationError, match="extra connections"):
        validator.validate(FullAction(), {"db": resource, "ghost": resource}, _action_node(FullAction))


def test_validate_rejects_unknown_keys_before_missing_message() -> None:
    validator = ConnectionValidator()
    resource = OrdersDbManager()
    with pytest.raises(ConnectionValidationError, match="extra connections"):
        validator.validate(FullAction(), {"wrong": resource}, _action_node(FullAction))


def test_validate_rejects_non_resource_values() -> None:
    validator = ConnectionValidator()
    with pytest.raises(ConnectionValidationError, match="must be an instance"):
        validator.validate(FullAction(), {"db": object()}, _action_node(FullAction))


def test_validate_returns_normalized_mapping_on_success() -> None:
    validator = ConnectionValidator()
    resource = OrdersDbManager()
    connections = {"db": resource}
    assert validator.validate(FullAction(), connections, _action_node(FullAction)) is connections


def test_validate_rejects_when_declared_subset_not_fully_provided() -> None:
    """Uses a stub node so multiple declared keys are visible without introducing a synthetic Action."""
    validator = ConnectionValidator()
    node = MagicMock()
    node.connection_keys.return_value = frozenset({"db", "cache"})
    resource = OrdersDbManager()
    with pytest.raises(ConnectionValidationError, match="missing required connections"):
        validator.validate(FullAction(), {"db": resource}, node)
