# tests/maxitor/test_interchange_graph_visualizer.py
"""Second-path G6 export for :class:`~graph.node_graph_coordinator.NodeGraphCoordinator` via :mod:`maxitor.viz2.interchange_graph_visualizer`."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import rustworkx as rx

from action_machine.application import Application
from action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode
from action_machine.graph_model.nodes.compensator_graph_node import CompensatorGraphNode
from action_machine.graph_model.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.base_graph_node_inspector import BaseGraphNodeInspector
from graph.composition_graph_edge import CompositionGraphEdge
from graph.exceptions import InvalidGraphError
from graph.node_graph_coordinator import NodeGraphCoordinator
from maxitor.viz2.interchange_graph_visualizer import (
    G6_CDN_URL,
    all_axis_graph_node_inspectors,
    generate_interchange_g6_html,
    interchange_edge_to_visual_dict,
    interchange_node_to_visual_dict,
    interchange_pygraph_for_g6,
)


class _TestGraphNode(BaseGraphNode[object]):
    def __init__(
        self,
        *,
        node_id: str,
        node_type: str,
        label: str,
        node_obj: object,
        edges: list[BaseGraphEdge] | None = None,
    ) -> None:
        self._edges = [] if edges is None else list(edges)
        super().__init__(
            node_id=node_id,
            node_type=node_type,
            label=label,
            properties={},
            node_obj=node_obj,
        )

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return self._edges


def test_interchange_node_and_edge_to_visual_dicts() -> None:
    n = ApplicationGraphNode(Application)
    d = interchange_node_to_visual_dict(n)
    assert d["id"] == n.node_id
    assert d["node_type"] == ApplicationGraphNode.NODE_TYPE
    assert "Application" in d["node_obj"]
    e = AssociationGraphEdge(
        edge_name="belongs_to",
        is_dag=False,
        target_node_id=n.node_id,
    )
    ed = interchange_edge_to_visual_dict(e)
    assert ed["edge_type"] == "belongs_to"
    assert ed["is_dag"] is False
    assert ed["relationship_name"] == "Association"
    assert ed["source_attachment"] == "none"
    assert ed["target_attachment"] == "open_arrow"
    assert ed["line_style"] == "solid"


def test_interchange_edge_visual_dict_swaps_composition_diamond_to_regular_aspect_target() -> None:
    """UML whole-part cap on the aspect end; interchange topology remains Action → aspect."""
    tgt = _TestGraphNode(
        node_id="pkg.Action:my_aspect",
        node_type=RegularAspectGraphNode.NODE_TYPE,
        label="Asp",
        node_obj=object(),
    )
    e = CompositionGraphEdge(
        edge_name="my_aspect",
        is_dag=False,
        target_node_id=tgt.node_id,
        target_node=tgt,
    )
    ed = interchange_edge_to_visual_dict(e)
    assert ed["source_attachment"] == "none"
    assert ed["target_attachment"] == "filled_diamond"


def test_interchange_edge_visual_dict_swaps_composition_diamond_to_summary_aspect_target() -> None:
    tgt = _TestGraphNode(
        node_id="pkg.Action:pong_summary",
        node_type=SummaryAspectGraphNode.NODE_TYPE,
        label="Sum",
        node_obj=object(),
    )
    e = CompositionGraphEdge(
        edge_name="pong_summary",
        is_dag=False,
        target_node_id=tgt.node_id,
        target_node=tgt,
    )
    ed = interchange_edge_to_visual_dict(e)
    assert ed["source_attachment"] == "none"
    assert ed["target_attachment"] == "filled_diamond"


def test_interchange_edge_visual_dict_swaps_composition_diamond_to_compensator_target() -> None:
    tgt = _TestGraphNode(
        node_id="pkg.Action:rollback_charge_compensate",
        node_type=CompensatorGraphNode.NODE_TYPE,
        label="Comp",
        node_obj=object(),
    )
    e = CompositionGraphEdge(
        edge_name="rollback_charge_compensate",
        is_dag=False,
        target_node_id=tgt.node_id,
        target_node=tgt,
    )
    ed = interchange_edge_to_visual_dict(e)
    assert ed["source_attachment"] == "none"
    assert ed["target_attachment"] == "filled_diamond"


def test_interchange_edge_visual_dict_swaps_composition_diamond_to_error_handler_target() -> None:
    tgt = _TestGraphNode(
        node_id="pkg.Action:handle_finalize_on_error",
        node_type=ErrorHandlerGraphNode.NODE_TYPE,
        label="Eh",
        node_obj=object(),
    )
    e = CompositionGraphEdge(
        edge_name="handle_finalize_on_error",
        is_dag=False,
        target_node_id=tgt.node_id,
        target_node=tgt,
    )
    ed = interchange_edge_to_visual_dict(e)
    assert ed["source_attachment"] == "none"
    assert ed["target_attachment"] == "filled_diamond"


class _PygraphRoundTripAxis:
    """Axis root for :func:`test_interchange_pygraph_for_g6_round_trip_topology` only."""


class _PygraphRoundTripInspector(BaseGraphNodeInspector[_PygraphRoundTripAxis]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return None

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        b = _TestGraphNode(
            node_id="tests.b",
            node_type="Params",
            label="B",
            node_obj=object(),
        )
        edge = AssociationGraphEdge(
            edge_name="params",
            is_dag=False,
            target_node_id="tests.b",
        )
        a = _TestGraphNode(
            node_id="tests.a",
            node_type="Action",
            label="A",
            edges=[edge],
            node_obj=object(),
        )
        return [a, b]


class _SingleHtmlAxis:
    """Axis root for minimal HTML smoke tests."""


class _SingleHtmlConcrete(_SingleHtmlAxis):
    """Strict subclass exercised by :class:`_SingleActionHtmlInspector`."""


class _SingleActionHtmlInspector(BaseGraphNodeInspector[_SingleHtmlAxis]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if cls is not _SingleHtmlConcrete:
            return None
        return _TestGraphNode(
            node_id="tests.html_only",
            node_type="Action",
            label="HtmlOnly",
            node_obj=object(),
        )


def test_interchange_pygraph_for_g6_round_trip_topology() -> None:
    coord = NodeGraphCoordinator()
    coord.build([_PygraphRoundTripInspector()])
    out = interchange_pygraph_for_g6(coord)
    assert out.num_nodes() == 2
    assert out.num_edges() == 1
    n0 = out[out.node_indices()[0]]
    assert isinstance(n0, dict) and n0["node_type"] == "Action"
    _, _, ew = next(iter(out.weighted_edge_list()))
    assert ew["edge_type"] == "params"
    assert ew["is_dag"] is False
    assert ew["relationship_name"] == "Association"
    assert ew["source_attachment"] == "none"
    assert ew["target_attachment"] == "open_arrow"
    assert ew["line_style"] == "solid"


def test_generate_interchange_g6_html_accepts_native_base_graph_nodes(tmp_path: Path) -> None:
    coord = NodeGraphCoordinator()
    coord.build([_SingleActionHtmlInspector()])
    html_path = tmp_path / "anchor.html"
    captured: list[str] = []

    def fake_write_text(_self: Path, data: str, *_args: object, **_kwargs: object) -> int:
        captured.append(data)
        return len(data)

    with patch.object(Path, "write_text", fake_write_text):
        written = generate_interchange_g6_html(coord, html_path, title="anchor only")
    assert written == html_path
    assert len(captured) == 1
    assert G6_CDN_URL in captured[0]


def test_all_axis_inspectors_count() -> None:
    assert len(all_axis_graph_node_inspectors()) == 8


class _BadRefAxis:
    """Axis root for :func:`test_coordinator_build_fails_on_dangling_edge_target`."""


class _BadRefLeaf(_BadRefAxis):
    """Strict subclass so :meth:`BaseGraphNodeInspector.get_graph_nodes` visits a row."""


class _BadRefInspector(BaseGraphNodeInspector[_BadRefAxis]):
    """Emits one domain-like node whose ``belongs_to`` points at a missing target id."""

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if cls is not _BadRefLeaf:
            return None
        dom = _TestGraphNode(
            node_id="tests.viz2.bad_domain",
            node_type="Domain",
            label="BadDomain",
            edges=[
                AssociationGraphEdge(
                    edge_name="belongs_to",
                    is_dag=False,
                    target_node_id="tests.viz2.MISSING_APPLICATION_TARGET",
                ),
            ],
            node_obj=object(),
        )
        return dom


def test_coordinator_build_fails_on_dangling_edge_target() -> None:
    """No viz2 helper may add missing vertices; the coordinator must reject dangling edges."""
    coord = NodeGraphCoordinator()
    with pytest.raises(InvalidGraphError, match="missing target_node_id"):
        coord.build([_BadRefInspector()])


def test_generate_interchange_g6_html_rejects_non_base_graph_node(tmp_path: Path) -> None:
    coord = NodeGraphCoordinator()
    coord.build([_SingleActionHtmlInspector()])
    bad = rx.PyDiGraph()
    bad.add_node({"node_type": "Action", "id": "x", "label": "X"})
    object.__setattr__(coord, "_rx_graph", bad)
    with pytest.raises(TypeError, match="BaseGraphNode"):
        generate_interchange_g6_html(coord, tmp_path / "bad.html")
