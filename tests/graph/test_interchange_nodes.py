# tests/graph/test_interchange_nodes.py
"""Interchange node types: graph_model nodes for params/result/action/domain/entity/aspects/compensators/on_error."""

from __future__ import annotations

from pydantic import Field

from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.domain.graph_model.entity_graph_node import EntityGraphNode
from action_machine.legacy.application_context_inspector import ApplicationContextInspector
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.compensator_graph_node import CompensatorGraphNode
from action_machine.model.graph_model.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.model.graph_model.result_graph_node import ResultGraphNode
from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode
from action_machine.tools import Introspection
from graph.base_graph_edge import BaseGraphEdge
from graph.edge_relationship import AGGREGATION, ASSOCIATION, COMPOSITION
from graph.facet_vertex import FacetVertex
from tests.scenarios.domain_model.child_action import ChildAction
from tests.scenarios.domain_model.compensate_actions import (
    CompensateAndOnErrorAction,
    CompensatedOrderAction,
)
from tests.scenarios.domain_model.domains import SystemDomain
from tests.scenarios.domain_model.entities import SampleEntity, TestDomain
from tests.scenarios.domain_model.ping_action import PingAction


def test_regular_aspect_graph_node_interchange_shape() -> None:
    node = RegularAspectGraphNode(ChildAction.process_aspect)
    assert node.node_obj is ChildAction.process_aspect
    assert node.node_type == RegularAspectGraphNode.NODE_TYPE
    assert node.label == "process_aspect"
    assert node.properties == {}
    assert node.edges == []
    assert node.node_id == f"{Introspection.full_qualname(ChildAction)}:process_aspect"


def test_summary_aspect_graph_node_interchange_shape() -> None:
    node = SummaryAspectGraphNode(PingAction.pong_summary)
    assert node.node_obj is PingAction.pong_summary
    assert node.node_type == SummaryAspectGraphNode.NODE_TYPE
    assert node.label == "pong_summary"
    assert node.properties == {}
    assert node.edges == []
    assert node.node_id == f"{Introspection.full_qualname(PingAction)}:pong_summary"


def test_compensator_graph_node_interchange_shape() -> None:
    node = CompensatorGraphNode(CompensatedOrderAction.rollback_charge_compensate)
    assert node.node_obj is CompensatedOrderAction.rollback_charge_compensate
    assert node.node_type == CompensatorGraphNode.NODE_TYPE
    assert node.label == "rollback_charge_compensate"
    assert node.properties == {}
    assert node.edges == []
    assert node.node_id == (
        f"{Introspection.full_qualname(CompensatedOrderAction)}:rollback_charge_compensate"
    )


def test_action_graph_node_get_compensator_edges() -> None:
    host = Introspection.full_qualname(CompensatedOrderAction)
    edges = ActionGraphNode.get_compensator_edges(CompensatedOrderAction)
    assert len(edges) == 2
    assert {e.target_node_id for e in edges} == {
        f"{host}:rollback_charge_compensate",
        f"{host}:rollback_reserve_compensate",
    }
    assert all(e.target_node_type == CompensatorGraphNode.NODE_TYPE for e in edges)
    assert all(e.edge_relationship is COMPOSITION for e in edges)


def test_error_handler_graph_node_interchange_shape() -> None:
    node = ErrorHandlerGraphNode(CompensateAndOnErrorAction.handle_finalize_on_error)
    assert node.node_obj is CompensateAndOnErrorAction.handle_finalize_on_error
    assert node.node_type == ErrorHandlerGraphNode.NODE_TYPE
    assert node.label == "handle_finalize_on_error"
    assert node.properties == {}
    assert node.edges == []
    assert node.node_id == (
        f"{Introspection.full_qualname(CompensateAndOnErrorAction)}:handle_finalize_on_error"
    )


def test_action_graph_node_get_error_handler_edges() -> None:
    host = Introspection.full_qualname(CompensateAndOnErrorAction)
    edges = ActionGraphNode.get_error_handler_edges(CompensateAndOnErrorAction)
    assert len(edges) == 1
    assert edges[0].target_node_id == f"{host}:handle_finalize_on_error"
    assert edges[0].target_node_type == ErrorHandlerGraphNode.NODE_TYPE
    assert edges[0].edge_relationship is COMPOSITION


def test_params_graph_node_interchange_shape() -> None:
    class PongParams(BaseParams):
        """Minimal params for node tests."""

        token: str = Field(description="Token")

    node = ParamsGraphNode(PongParams)
    assert node.node_obj is PongParams
    assert node.node_type == "Params"
    assert node.label == "PongParams"
    assert node.node_id == Introspection.full_qualname(PongParams)
    assert node.properties == {}
    assert node.edges == []


def test_result_graph_node_interchange_shape() -> None:
    class PongResult(BaseResult):
        """Minimal result for node tests."""

        ok: bool = Field(description="Ok")

    node = ResultGraphNode(PongResult)
    assert node.node_obj is PongResult
    assert node.node_type == "Result"
    assert node.label == "PongResult"
    assert node.node_id == Introspection.full_qualname(PongResult)
    assert node.properties == {}
    assert node.edges == []


def test_domain_node_interchange_shape() -> None:
    node = DomainGraphNode(TestDomain)
    assert node.node_obj is TestDomain
    assert node.node_id == Introspection.full_qualname(TestDomain)
    assert node.node_type == "Domain"
    assert node.node_type == "Domain"
    assert node.label == "TestDomain"
    assert node.node_id == Introspection.full_qualname(TestDomain)
    assert node.properties == {
        "name": TestDomain.name,
        "description": TestDomain.description,
    }
    assert node.edges == []

    from_facets = ApplicationContextInspector._domain_payload_or_none(TestDomain)
    assert from_facets is not None
    assert from_facets.edges[0].target_node_type == "Application"
    # Interchange row omits ``belongs_to`` until an ``Application`` node exists in the same graph;
    # facet layer still carries the structural ``belongs_to`` edge.
    from_node = FacetVertex(
        node_type=node.node_type,
        node_name=node.node_id,
        node_class=node.node_obj,
        node_meta=tuple(node.properties.items()),
        edges=(),
    )
    assert from_node.node_type == from_facets.node_type
    assert from_node.node_name == from_facets.node_name
    assert from_node.node_class is from_facets.node_class
    assert dict(from_node.node_meta) == dict(from_facets.node_meta)


def test_action_graph_node_links_and_helpers() -> None:
    node = ActionGraphNode(PingAction)
    assert node.node_obj is PingAction
    dom_id = Introspection.full_qualname(SystemDomain)
    params_id = Introspection.full_qualname(PingAction.Params)
    result_id = Introspection.full_qualname(PingAction.Result)
    host = Introspection.full_qualname(PingAction)

    assert node.node_type == "Action"
    assert node.label == "PingAction"
    assert node.node_id == host
    assert node.edges == [
        BaseGraphEdge(
            edge_name="domain",
            is_dag=True,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            target_node_id=dom_id,
            target_node_type="Domain",
            target_node_obj=SystemDomain,
            edge_relationship=ASSOCIATION,
        ),
        BaseGraphEdge(
            edge_name="params",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            target_node_id=params_id,
            target_node_type="Params",
            target_node_obj=PingAction.Params,
            edge_relationship=AGGREGATION,
        ),
        BaseGraphEdge(
            edge_name="result",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            target_node_id=result_id,
            target_node_type="Result",
            target_node_obj=PingAction.Result,
            edge_relationship=AGGREGATION,
        ),
        BaseGraphEdge(
            edge_name="pong_summary",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            target_node_id=f"{host}:pong_summary",
            target_node_type=SummaryAspectGraphNode.NODE_TYPE,
            target_node_obj=PingAction.pong_summary,
            edge_relationship=COMPOSITION,
        ),
    ]

    assert ActionGraphNode.get_domain_edge(PingAction) == BaseGraphEdge(
        edge_name="domain",
        is_dag=True,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        target_node_id=dom_id,
        target_node_type="Domain",
        target_node_obj=SystemDomain,
        edge_relationship=ASSOCIATION,
    )
    assert ActionGraphNode.get_params_edge(PingAction) == BaseGraphEdge(
        edge_name="params",
        is_dag=False,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        target_node_id=params_id,
        target_node_type="Params",
        target_node_obj=PingAction.Params,
        edge_relationship=AGGREGATION,
    )
    assert ActionGraphNode.get_result_edge(PingAction) == BaseGraphEdge(
        edge_name="result",
        is_dag=False,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        target_node_id=result_id,
        target_node_type="Result",
        target_node_obj=PingAction.Result,
        edge_relationship=AGGREGATION,
    )

    p_type = ActionGraphNode.get_schema_generic_binding(PingAction, 0)
    r_type = ActionGraphNode.get_schema_generic_binding(PingAction, 1)
    assert p_type is PingAction.Params and r_type is PingAction.Result
    assert Introspection.full_qualname(p_type) == params_id
    assert Introspection.full_qualname(r_type) == result_id


def test_entity_node_links_properties_and_domain_helpers() -> None:
    node = EntityGraphNode(SampleEntity)
    assert node.node_obj is SampleEntity
    dom_id = Introspection.full_qualname(TestDomain)
    host = Introspection.full_qualname(SampleEntity)

    assert node.node_type == "Entity"
    assert node.label == "SampleEntity"
    assert node.node_id == host
    assert node.properties == {"description": "Simple test entity"}
    assert node.edges == [
        BaseGraphEdge(
            edge_name="domain",
            is_dag=False,
            source_node_id=host,
            source_node_type="Entity",
            source_node_obj=SampleEntity,
            target_node_id=dom_id,
            target_node_type="Domain",
            target_node_obj=TestDomain,
            edge_relationship=ASSOCIATION,
        ),
    ]

    assert EntityGraphNode.get_domain_edge(SampleEntity) == BaseGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id=host,
        source_node_type="Entity",
        source_node_obj=SampleEntity,
        target_node_id=dom_id,
        target_node_type="Domain",
        target_node_obj=TestDomain,
        edge_relationship=ASSOCIATION,
    )
    assert EntityGraphNode._get_all_edges(SampleEntity) == node.edges
