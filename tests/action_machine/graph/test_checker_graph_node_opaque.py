# tests/action_machine/graph/test_checker_graph_node_opaque.py
"""Unit tests for opaque field on CheckerGraphNode, CheckerGraphPayload, and CheckerGraphEdge."""

from __future__ import annotations

from aoa.action_machine.graph.edges.checker_graph_edge import CheckerGraphEdge
from aoa.action_machine.graph.nodes.checker_graph_node import CheckerGraphNode
from aoa.action_machine.intents.checkers.result_string_decorator import FieldStringChecker

# ─────────────────────────────────────────────────────────────────────────────
# Minimal fixtures
# ─────────────────────────────────────────────────────────────────────────────


class _OwnerAction:
    """Stub action class used as _action_cls in tests."""


def _aspect_method() -> None:
    """Stub aspect callable — only its __name__ is used by CheckerGraphNode."""


# ─────────────────────────────────────────────────────────────────────────────
# CheckerGraphNode opaque storage
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckerGraphNodeOpaquePayload:
    """CheckerGraphNode stores opaque flag on its payload."""

    def test_default_opaque_is_false(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="name",
        )
        assert node.node_obj.opaque is False

    def test_opaque_true_stored_on_payload(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="name",
            opaque=True,
        )
        assert node.node_obj.opaque is True

    def test_required_and_opaque_are_independent(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="name",
            required=True,
            opaque=True,
        )
        assert node.node_obj.required is True
        assert node.node_obj.opaque is True


# ─────────────────────────────────────────────────────────────────────────────
# to_dict includes opaque
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckerGraphNodeToDict:
    """to_dict() always includes 'opaque' in properties."""

    def test_to_dict_opaque_false(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="title",
            opaque=False,
        )
        d = node.to_dict()
        assert "opaque" in d["properties"]
        assert d["properties"]["opaque"] is False

    def test_to_dict_opaque_true(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="title",
            opaque=True,
        )
        d = node.to_dict()
        assert d["properties"]["opaque"] is True

    def test_to_dict_required_also_present(self) -> None:
        node = CheckerGraphNode(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            checker_class=FieldStringChecker,
            field_name="title",
            required=True,
            opaque=True,
        )
        d = node.to_dict()
        assert d["properties"]["required"] is True
        assert d["properties"]["opaque"] is True


# ─────────────────────────────────────────────────────────────────────────────
# CheckerGraphEdge._build_checker_node reads opaque from meta row
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckerGraphEdgeBuildOpaque:
    """_build_checker_node reads opaque from the meta row dict."""

    def test_opaque_true_from_row(self) -> None:
        row = {
            "checker_class": FieldStringChecker,
            "field_name": "secret",
            "required": True,
            "opaque": True,
        }
        node = CheckerGraphEdge._build_checker_node(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            row=row,
        )
        assert node is not None
        assert node.node_obj.opaque is True

    def test_opaque_false_from_row(self) -> None:
        row = {
            "checker_class": FieldStringChecker,
            "field_name": "plain",
            "required": True,
            "opaque": False,
        }
        node = CheckerGraphEdge._build_checker_node(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            row=row,
        )
        assert node is not None
        assert node.node_obj.opaque is False

    def test_opaque_absent_from_row_defaults_to_false(self) -> None:
        row = {
            "checker_class": FieldStringChecker,
            "field_name": "plain",
        }
        node = CheckerGraphEdge._build_checker_node(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            row=row,
        )
        assert node is not None
        assert node.node_obj.opaque is False

    def test_opaque_not_in_extra_props(self) -> None:
        """'opaque' must be extracted from row, not leaked into extra_props."""
        row = {
            "checker_class": FieldStringChecker,
            "field_name": "plain",
            "opaque": True,
        }
        node = CheckerGraphEdge._build_checker_node(
            aspect_callable=_aspect_method,
            _action_cls=_OwnerAction,
            row=row,
        )
        assert node is not None
        # opaque is a named payload field, not a free-form property key
        assert node.node_obj.opaque is True
        # It should appear in properties dict (merged), not as an unexpected extra
        assert "opaque" in node.properties
