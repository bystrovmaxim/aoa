"""Extra coverage tests for new metadata GraphCoordinator."""

from __future__ import annotations

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.exceptions import (
    DuplicateNodeError,
    InvalidGraphError,
    PayloadValidationError,
)
from action_machine.graph.facet_edge import FacetEdge
from action_machine.graph.facet_vertex import FacetVertex
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.runtime.machines.core import Core


class _A:
    pass


class _B:
    pass


class _M:
    pass


class _InspectorA(BaseIntentInspector):
    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return [_A]

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        return FacetVertex(node_type="a", node_name="A", node_class=target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        raise NotImplementedError


class _InspectorDup(BaseIntentInspector):
    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return [_B]

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        return FacetVertex(node_type="a", node_name="A", node_class=target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        raise NotImplementedError


def test_build_status_transitions() -> None:
    coord = GraphCoordinator()
    assert coord.build_status() == "not_built"
    coord.register(_InspectorA).build()
    assert coord.build_status() == "built"
    assert coord.is_built is True


def test_build_and_graph_read_api() -> None:
    coord = GraphCoordinator().register(_InspectorA).build()
    assert coord.is_built is True
    assert len(coord.facet_topology_copy()) == 1
    assert coord.graph_node_count == len(coord.get_graph())
    assert coord.get_node("a", "A") is not None
    assert coord.get_node("a", "A") is not None
    assert len(coord.get_nodes_by_type("a")) == 1
    assert len(coord.get_nodes_for_class(_A)) == 1
    assert "GraphCoordinator(" in repr(coord)
    graph_copy = coord.get_graph()
    assert graph_copy.num_nodes() == coord.graph_node_count


def test_register_guards_and_duplicate_build() -> None:
    coord = GraphCoordinator().register(_InspectorA)
    with pytest.raises(ValueError):
        coord.register(_InspectorA)
    coord.build()
    with pytest.raises(RuntimeError):
        coord.register(_InspectorDup)
    with pytest.raises(RuntimeError):
        coord.build()


def test_duplicate_node_error_from_phase1() -> None:
    coord = (
        GraphCoordinator()
        .register(_InspectorA)
        .register(_InspectorDup)
    )
    with pytest.raises(DuplicateNodeError):
        coord.build()


def test_payload_validation_and_phase2_errors() -> None:
    coord = GraphCoordinator()
    with pytest.raises(PayloadValidationError):
        coord._phase2_check_payloads([  # pylint: disable=protected-access
            FacetVertex(node_type="", node_name="x", node_class=_A)
        ])
    with pytest.raises(PayloadValidationError):
        coord._phase2_check_payloads([  # pylint: disable=protected-access
            FacetVertex(node_type="x", node_name="", node_class=_A)
        ])
    with pytest.raises(PayloadValidationError):
        coord._phase2_check_payloads([  # pylint: disable=protected-access
            FacetVertex(node_type="x", node_name="y", node_class=object())
        ])


def test_referential_integrity_and_acyclicity_errors() -> None:
    coord = GraphCoordinator()
    payloads = [
        FacetVertex(
            node_type="x",
            node_name="n1",
            node_class=_A,
            edges=(FacetEdge("x", "missing", "depends", True),),
        ),
    ]
    with pytest.raises(InvalidGraphError):
        coord._phase2_check_referential_integrity(payloads)  # pylint: disable=protected-access

    cyc = [
        FacetVertex(
            node_type="x",
            node_name="n1",
            node_class=_A,
            edges=(FacetEdge("x", "n2", "depends", True),),
        ),
        FacetVertex(
            node_type="x",
            node_name="n2",
            node_class=_B,
            edges=(FacetEdge("x", "n1", "depends", True),),
        ),
    ]
    with pytest.raises(InvalidGraphError):
        coord._phase2_check_acyclicity(cyc)  # pylint: disable=protected-access


def test_default_coordinator_factory_builds() -> None:
    coord = Core.create_coordinator()
    assert coord.is_built is True
    assert coord.graph_node_count > 0
