# tests/test_fastapi_permissions.py
"""
Tests for ``aoa.fastapi.permissions`` — ``operation`` name resolution (issue #130, PR 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate ``build_action_index``/``resolve_action_class`` against a lightweight
fake coordinator exposing only the slice of ``NodeGraphCoordinator`` these
functions actually use (``get_nodes_by_type`` returning objects with ``.label``/
``.node_obj``) — isolated from the real graph-building machinery, which is
already covered by ``aoa-action-machine``'s own graph tests.
"""

from dataclasses import dataclass
from typing import Any

import pytest

from aoa.fastapi.permissions import build_action_index, resolve_action_class


@dataclass(frozen=True)
class _FakeNode:
    """Stand-in for ``ActionGraphNode`` exposing only ``label``/``node_obj``."""

    label: str
    node_obj: type


class _FakeCoordinator:
    """Stand-in for ``NodeGraphCoordinator`` exposing only ``get_nodes_by_type``."""

    def __init__(self, nodes: list[_FakeNode]) -> None:
        self._nodes = nodes

    def get_nodes_by_type(self, node_type: str) -> tuple[Any, ...]:
        return tuple(self._nodes)


class CancelOrderAction:
    """Stand-in action class — identity matters, not real ``BaseAction`` behavior."""


class IssueRefundAction:
    """Stand-in action class — identity matters, not real ``BaseAction`` behavior."""


class TestBuildActionIndex:
    """``build_action_index`` — ``{bare class name: action class}`` from graph nodes."""

    def test_empty_graph_yields_empty_index(self) -> None:
        """No registered actions -> empty index, not an error."""
        index = build_action_index(_FakeCoordinator([]))
        assert index == {}

    def test_indexes_by_bare_class_name(self) -> None:
        """Each node's ``label`` (bare ``__name__``) becomes the lookup key."""
        coordinator = _FakeCoordinator(
            [
                _FakeNode(label="CancelOrderAction", node_obj=CancelOrderAction),
                _FakeNode(label="IssueRefundAction", node_obj=IssueRefundAction),
            ]
        )
        index = build_action_index(coordinator)
        assert index == {"CancelOrderAction": CancelOrderAction, "IssueRefundAction": IssueRefundAction}

    def test_same_class_listed_twice_is_not_a_duplicate(self) -> None:
        """Re-seeing the identical class object under its own name is not an error."""
        coordinator = _FakeCoordinator(
            [
                _FakeNode(label="CancelOrderAction", node_obj=CancelOrderAction),
                _FakeNode(label="CancelOrderAction", node_obj=CancelOrderAction),
            ]
        )
        index = build_action_index(coordinator)
        assert index == {"CancelOrderAction": CancelOrderAction}

    def test_two_different_classes_same_name_raises(self) -> None:
        """Two distinct classes sharing a bare name is a configuration error caught here, not per-request."""
        first = type("DuplicateAction", (), {})
        second = type("DuplicateAction", (), {})
        coordinator = _FakeCoordinator(
            [
                _FakeNode(label="DuplicateAction", node_obj=first),
                _FakeNode(label="DuplicateAction", node_obj=second),
            ]
        )
        with pytest.raises(ValueError, match="DuplicateAction"):
            build_action_index(coordinator)


class TestResolveActionClass:
    """``resolve_action_class`` — look up one action class by wire ``operation`` name."""

    def test_returns_registered_class(self) -> None:
        """A known operation name resolves to its action class."""
        index = {"CancelOrderAction": CancelOrderAction}
        assert resolve_action_class("CancelOrderAction", index) is CancelOrderAction

    def test_unknown_operation_raises_lookup_error(self) -> None:
        """An unregistered operation name fails the whole request (no per-item isolation in this PR)."""
        with pytest.raises(LookupError, match="NoSuchAction"):
            resolve_action_class("NoSuchAction", {"CancelOrderAction": CancelOrderAction})
