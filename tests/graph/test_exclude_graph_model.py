# tests/graph/test_exclude_graph_model.py
"""Tests for :mod:`graph.exclude_graph_model`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pytest

from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.exclude_graph_model import exclude_graph_model, excluded_from_graph_model


def test_exclude_graph_model_raises_on_non_class() -> None:
    with pytest.raises(TypeError, match="only to classes"):
        exclude_graph_model(object())  # type: ignore[arg-type]


def test_excluded_from_graph_model_false_for_instances() -> None:
    class _C:
        pass

    assert excluded_from_graph_model(_C()) is False


def test_excluded_from_graph_model_reflects_decorator() -> None:
    @exclude_graph_model
    class _Marked:
        pass

    class _Plain:
        pass

    assert excluded_from_graph_model(_Marked)
    assert not excluded_from_graph_model(_Plain)
    exclude_graph_model(_Marked)  # repeat — still marked
    assert excluded_from_graph_model(_Marked)


def test_excluded_from_graph_model_not_inherited_by_subclasses() -> None:
    @exclude_graph_model
    class _Marked:
        pass

    class _Child(_Marked):
        pass

    assert excluded_from_graph_model(_Marked)
    assert not excluded_from_graph_model(_Child)


def test_should_skip_axis_host_honours_marker() -> None:
    """``BaseGraphNodeInspector`` must not call ``_get_node`` for excluded hosts."""

    class _Axis(ABC):
        @abstractmethod
        def _slot(self) -> None:
            """Keeps the axis abstract so the root is omitted from the walk."""

    @exclude_graph_model
    class _Hidden(_Axis):
        def _slot(self) -> None:
            return None

    class _Visible(_Axis):
        def _slot(self) -> None:
            return None

    n_visible = _stub_node("visible")

    class _Inspector(BaseGraphNodeInspector[_Axis]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            if cls is _Hidden:
                raise AssertionError("_get_node must not run for excluded class")
            if cls is _Visible:
                return n_visible
            raise AssertionError(f"unexpected cls {cls!r}")

    assert _Inspector().get_graph_nodes() == [n_visible]


def _stub_node(node_id: str) -> BaseGraphNode[object]:
    class _N(BaseGraphNode[object]):
        def __init__(self) -> None:
            super().__init__(
                node_id=node_id,
                node_type="Test",
                label="L",
                properties={},
                node_obj=object(),
            )

        def get_all_edges(self) -> list[BaseGraphEdge]:
            return []

    return _N()
