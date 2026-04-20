# tests/graph/test_interchange_nodes.py
"""Interchange node types: ``ParamsNode``, ``ResultNode``, ``DomainGraphNode``, ``ActionNode``, and ``EntityGraphNode``."""

from __future__ import annotations

from pydantic import Field

from action_machine.domain.domain_graph_node import DomainGraphNode
from action_machine.domain.entity_graph_node import EntityGraphNode
from action_machine.legacy.application_context import ApplicationContext
from action_machine.legacy.application_context_inspector import ApplicationContextInspector
from action_machine.model.action_node import ActionNode
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.params_node import ParamsNode
from action_machine.model.result_node import ResultNode
from graph.base_graph_edge import BaseGraphEdge
from graph.edge_relationship import EdgeRelationship
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex
from graph.qualified_name import cls_qualified_dotted_id
from tests.scenarios.domain_model.domains import SystemDomain
from tests.scenarios.domain_model.entities import SampleEntity, TestDomain
from tests.scenarios.domain_model.ping_action import PingAction


def test_params_node_interchange_shape() -> None:
    class PongParams(BaseParams):
        """Minimal params for node tests."""

        token: str = Field(description="Token")

    node = ParamsNode(PongParams)
    assert node.node_obj is PongParams
    assert node.node_type == "params_schema"
    assert node.label == "PongParams"
    assert node.node_id == cls_qualified_dotted_id(PongParams)
    assert node.properties == {}
    assert node.edges == []


def test_result_node_interchange_shape() -> None:
    class PongResult(BaseResult):
        """Minimal result for node tests."""

        ok: bool = Field(description="Ok")

    node = ResultNode(PongResult)
    assert node.node_obj is PongResult
    assert node.node_type == "result_schema"
    assert node.label == "PongResult"
    assert node.node_id == cls_qualified_dotted_id(PongResult)
    assert node.properties == {}
    assert node.edges == []


def test_domain_node_interchange_shape() -> None:
    node = DomainGraphNode(TestDomain)
    assert node.node_obj is TestDomain
    assert node.node_id == cls_qualified_dotted_id(TestDomain)
    assert node.node_type == "Domain"
    assert node.node_type == "Domain"
    assert node.label == "TestDomain"
    assert node.node_id == cls_qualified_dotted_id(TestDomain)
    assert node.properties == {
        "name": TestDomain.name,
        "description": TestDomain.description,
    }
    app_id = cls_qualified_dotted_id(ApplicationContext)
    assert node.edges == [
        BaseGraphEdge(
            edge_name="belongs_to",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(TestDomain),
            source_node_type="Domain",
            source_node_obj=TestDomain,
            source_node_relationship=EdgeRelationship.COMPOSITION,
            target_node_id=app_id,
            target_node_type="Application",
            target_node_obj=ApplicationContext,
            target_node_relationship=EdgeRelationship.ASSOCIATION,
        ),
    ]

    from_facets = ApplicationContextInspector._domain_payload_or_none(TestDomain)
    assert from_facets is not None
    assert from_facets.edges[0].target_node_type == "Application"
    from_node = FacetVertex(
        node_type=node.node_type,
        node_name=node.node_id,
        node_class=node.node_obj,
        node_meta=tuple(node.properties.items()),
        edges=tuple(
            FacetEdge(
                target_node_type=fe.target_node_type,
                target_name=e.target_node_id,
                edge_type=e.edge_name,
                is_structural=e.is_dag,
                edge_meta=(),
                target_class_ref=fe.target_class_ref,
            )
            for e, fe in zip(node.edges, from_facets.edges, strict=True)
        ),
    )
    assert from_node.node_type == from_facets.node_type
    assert from_node.node_name == from_facets.node_name
    assert from_node.node_class is from_facets.node_class
    assert dict(from_node.node_meta) == dict(from_facets.node_meta)
    assert from_node.edges == from_facets.edges


def test_action_node_links_and_helpers() -> None:
    node = ActionNode(PingAction)
    assert node.node_obj is PingAction
    dom_id = cls_qualified_dotted_id(SystemDomain)
    params_id = cls_qualified_dotted_id(PingAction.Params)
    result_id = cls_qualified_dotted_id(PingAction.Result)
    host = cls_qualified_dotted_id(PingAction)

    assert node.node_type == "Action"
    assert node.label == "PingAction"
    assert node.node_id == host
    assert node.edges == [
        BaseGraphEdge(
            edge_name="domain",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            source_node_relationship=EdgeRelationship.ASSOCIATION,
            target_node_id=dom_id,
            target_node_type="Domain",
            target_node_obj=SystemDomain,
            target_node_relationship=EdgeRelationship.ASSOCIATION,
        ),
        BaseGraphEdge(
            edge_name="params",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            source_node_relationship=EdgeRelationship.FLOW,
            target_node_id=params_id,
            target_node_type="params_schema",
            target_node_obj=PingAction.Params,
            target_node_relationship=EdgeRelationship.REALIZATION,
        ),
        BaseGraphEdge(
            edge_name="result",
            is_dag=False,
            source_node_id=host,
            source_node_type="Action",
            source_node_obj=PingAction,
            source_node_relationship=EdgeRelationship.FLOW,
            target_node_id=result_id,
            target_node_type="result_schema",
            target_node_obj=PingAction.Result,
            target_node_relationship=EdgeRelationship.REALIZATION,
        ),
    ]

    assert ActionNode.get_domain_edge(PingAction) == BaseGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        source_node_relationship=EdgeRelationship.ASSOCIATION,
        target_node_id=dom_id,
        target_node_type="Domain",
        target_node_obj=SystemDomain,
        target_node_relationship=EdgeRelationship.ASSOCIATION,
    )
    assert ActionNode.get_params_edge(PingAction) == BaseGraphEdge(
        edge_name="params",
        is_dag=False,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        source_node_relationship=EdgeRelationship.FLOW,
        target_node_id=params_id,
        target_node_type="params_schema",
        target_node_obj=PingAction.Params,
        target_node_relationship=EdgeRelationship.REALIZATION,
    )
    assert ActionNode.get_result_edge(PingAction) == BaseGraphEdge(
        edge_name="result",
        is_dag=False,
        source_node_id=host,
        source_node_type="Action",
        source_node_obj=PingAction,
        source_node_relationship=EdgeRelationship.FLOW,
        target_node_id=result_id,
        target_node_type="result_schema",
        target_node_obj=PingAction.Result,
        target_node_relationship=EdgeRelationship.REALIZATION,
    )

    p_type = ActionNode.get_schema_generic_binding(PingAction, 0)
    r_type = ActionNode.get_schema_generic_binding(PingAction, 1)
    assert p_type is PingAction.Params and r_type is PingAction.Result
    assert cls_qualified_dotted_id(p_type) == params_id
    assert cls_qualified_dotted_id(r_type) == result_id


def test_entity_node_links_properties_and_domain_helpers() -> None:
    node = EntityGraphNode(SampleEntity)
    assert node.node_obj is SampleEntity
    dom_id = cls_qualified_dotted_id(TestDomain)
    host = cls_qualified_dotted_id(SampleEntity)

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
            source_node_relationship=EdgeRelationship.ASSOCIATION,
            target_node_id=dom_id,
            target_node_type="Domain",
            target_node_obj=TestDomain,
            target_node_relationship=EdgeRelationship.ASSOCIATION,
        ),
    ]

    assert EntityGraphNode.get_domain_edge(SampleEntity) == BaseGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id=host,
        source_node_type="Entity",
        source_node_obj=SampleEntity,
        source_node_relationship=EdgeRelationship.ASSOCIATION,
        target_node_id=dom_id,
        target_node_type="Domain",
        target_node_obj=TestDomain,
        target_node_relationship=EdgeRelationship.ASSOCIATION,
    )
    assert EntityGraphNode._get_all_edges(SampleEntity) == node.edges
