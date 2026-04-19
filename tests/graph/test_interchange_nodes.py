# tests/graph/test_interchange_nodes.py
"""Interchange node types: ``ParamsNode``, ``ResultNode``, ``DomainGraphNode``, ``ActionNode``, ``EntityGraphNode``, and ``BaseGraphNode`` parse error."""

from __future__ import annotations

import warnings

import pytest
from pydantic import Field

from action_machine.common import qualified_dotted_name
from action_machine.application.application_context import ApplicationContext
from action_machine.application.application_context_inspector import ApplicationContextInspector
from action_machine.domain.domain_graph_node import DomainGraphNode
from action_machine.domain.entity_graph_node import EntityGraphNode
from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode, BaseGraphNodeParseError
from action_machine.legacy.interchange_vertex_labels import APPLICATION_VERTEX_TYPE, DOMAIN_VERTEX_TYPE
from action_machine.model.action_node import ActionNode
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.params_node import ParamsNode
from action_machine.model.result_node import ResultNode

from tests.scenarios.domain_model.domains import SystemDomain
from tests.scenarios.domain_model.entities import SampleEntity, TestDomain
from tests.scenarios.domain_model.ping_action import PingAction


def test_base_graph_node_parse_raises_when_not_overridden() -> None:
    with pytest.raises(BaseGraphNodeParseError, match="not implemented"):
        BaseGraphNode(object())


def test_params_node_interchange_shape() -> None:
    class PongParams(BaseParams):
        """Minimal params for node tests."""

        token: str = Field(description="Token")

    node = ParamsNode(PongParams)
    assert node.obj is PongParams
    assert node.node_type == "params_schema"
    assert node.label == "PongParams"
    assert node.id == qualified_dotted_name(PongParams)
    assert node.properties == {}
    assert node.edges == []


def test_result_node_interchange_shape() -> None:
    class PongResult(BaseResult):
        """Minimal result for node tests."""

        ok: bool = Field(description="Ok")

    node = ResultNode(PongResult)
    assert node.obj is PongResult
    assert node.node_type == "result_schema"
    assert node.label == "PongResult"
    assert node.id == qualified_dotted_name(PongResult)
    assert node.properties == {}
    assert node.edges == []


def test_domain_node_interchange_shape() -> None:
    node = DomainGraphNode(TestDomain)
    assert node.obj is TestDomain
    assert node.payload.id == node.id == qualified_dotted_name(TestDomain)
    assert node.payload.node_type == node.node_type == "Domain"
    assert node.node_type == "Domain"
    assert node.label == "TestDomain"
    assert node.id == qualified_dotted_name(TestDomain)
    assert node.properties == {
        "name": TestDomain.name,
        "description": TestDomain.description,
    }
    app_id = qualified_dotted_name(ApplicationContext)
    assert node.edges == [
        BaseGraphEdge(
            link_name="belongs_to",
            target_id=app_id,
            target_node_type=APPLICATION_VERTEX_TYPE,
            is_dag=False,
            target_cls=ApplicationContext,
        ),
    ]

    from_facets = ApplicationContextInspector._domain_payload_or_none(TestDomain)
    assert from_facets is not None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from_node = node.to_facet_vertex()
    assert from_node.node_type == from_facets.node_type
    assert from_node.node_name == from_facets.node_name
    assert from_node.node_class is from_facets.node_class
    assert dict(from_node.node_meta) == dict(from_facets.node_meta)
    assert from_node.edges == from_facets.edges


def test_action_node_links_and_helpers() -> None:
    node = ActionNode(PingAction)
    assert node.obj is PingAction
    dom_id = qualified_dotted_name(SystemDomain)
    params_id = qualified_dotted_name(PingAction.Params)
    result_id = qualified_dotted_name(PingAction.Result)
    host = qualified_dotted_name(PingAction)

    assert node.node_type == "Action"
    assert node.label == "PingAction"
    assert node.id == host
    assert node.edges == [
        BaseGraphEdge(
            link_name="domain",
            target_id=dom_id,
            target_node_type=DOMAIN_VERTEX_TYPE,
            is_dag=False,
            target_cls=SystemDomain,
        ),
        BaseGraphEdge(
            link_name="params",
            target_id=params_id,
            target_node_type="params_schema",
            is_dag=False,
            target_cls=PingAction.Params,
        ),
        BaseGraphEdge(
            link_name="result",
            target_id=result_id,
            target_node_type="result_schema",
            is_dag=False,
            target_cls=PingAction.Result,
        ),
    ]

    assert ActionNode.get_domain_link(PingAction) == BaseGraphEdge(
        link_name="domain",
        target_id=dom_id,
        target_node_type=DOMAIN_VERTEX_TYPE,
        is_dag=False,
        target_cls=SystemDomain,
    )
    assert ActionNode.get_params_link(PingAction) == BaseGraphEdge(
        link_name="params",
        target_id=params_id,
        target_node_type="params_schema",
        is_dag=False,
        target_cls=PingAction.Params,
    )
    assert ActionNode.get_result_link(PingAction) == BaseGraphEdge(
        link_name="result",
        target_id=result_id,
        target_node_type="result_schema",
        is_dag=False,
        target_cls=PingAction.Result,
    )

    p_type, r_type = ActionNode.get_schema_generic_binding(PingAction)
    assert p_type is PingAction.Params and r_type is PingAction.Result
    assert qualified_dotted_name(p_type) == params_id
    assert qualified_dotted_name(r_type) == result_id


def test_entity_node_links_properties_and_domain_helpers() -> None:
    node = EntityGraphNode(SampleEntity)
    assert node.obj is SampleEntity
    dom_id = qualified_dotted_name(TestDomain)
    host = qualified_dotted_name(SampleEntity)

    assert node.node_type == "Entity"
    assert node.label == "SampleEntity"
    assert node.id == host
    assert node.properties == {"description": "Simple test entity"}
    assert node.edges == [
        BaseGraphEdge(
            link_name="domain",
            target_id=dom_id,
            target_node_type=DOMAIN_VERTEX_TYPE,
            is_dag=False,
            target_cls=TestDomain,
        ),
    ]

    assert EntityGraphNode.get_domain_link(SampleEntity) == BaseGraphEdge(
        link_name="domain",
        target_id=dom_id,
        target_node_type=DOMAIN_VERTEX_TYPE,
        is_dag=False,
        target_cls=TestDomain,
    )
    assert EntityGraphNode._get_all_edges(SampleEntity) == node.edges
