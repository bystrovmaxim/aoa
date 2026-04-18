# tests/graph/test_interchange_nodes.py
"""Interchange node types: ``ParamsNode``, ``ResultNode``, ``DomainNode``, ``ActionNode``, ``EntityNode``, and ``BaseGraphNode`` parse error."""

from __future__ import annotations

import pytest
from pydantic import Field

from action_machine.common import qualified_dotted_name
from action_machine.domain.domain_node import DomainNode
from action_machine.domain.entity_node import EntityNode
from action_machine.graph.base_graph_edge import BaseGraphEdge
from action_machine.graph.base_graph_node import BaseGraphNode, BaseGraphNodeParseError
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
    assert node.node_type == "Params"
    assert node.label == "PongParams"
    assert node.id == qualified_dotted_name(PongParams)
    assert node.properties == {}
    assert node.links == []


def test_result_node_interchange_shape() -> None:
    class PongResult(BaseResult):
        """Minimal result for node tests."""

        ok: bool = Field(description="Ok")

    node = ResultNode(PongResult)
    assert node.node_type == "Result"
    assert node.label == "PongResult"
    assert node.id == qualified_dotted_name(PongResult)
    assert node.properties == {}
    assert node.links == []


def test_domain_node_interchange_shape() -> None:
    node = DomainNode(TestDomain)
    assert node.node_type == "Domain"
    assert node.label == "TestDomain"
    assert node.id == qualified_dotted_name(TestDomain)
    assert node.properties == {}
    assert node.links == []


def test_action_node_links_and_helpers() -> None:
    node = ActionNode(PingAction)
    dom_id = qualified_dotted_name(SystemDomain)
    params_id = qualified_dotted_name(PingAction.Params)
    result_id = qualified_dotted_name(PingAction.Result)
    host = qualified_dotted_name(PingAction)

    assert node.node_type == "Action"
    assert node.label == "PingAction"
    assert node.id == host
    assert node.links == [
        BaseGraphEdge(link_name="domain", target_id=dom_id),
        BaseGraphEdge(link_name="params", target_id=params_id),
        BaseGraphEdge(link_name="result", target_id=result_id),
    ]

    assert ActionNode.get_domain_link(PingAction) == BaseGraphEdge(
        link_name="domain",
        target_id=dom_id,
    )
    assert ActionNode.get_params_link(PingAction) == BaseGraphEdge(
        link_name="params",
        target_id=params_id,
    )
    assert ActionNode.get_result_link(PingAction) == BaseGraphEdge(
        link_name="result",
        target_id=result_id,
    )

    p_type, r_type = ActionNode.get_schema_generic_binding(PingAction)
    assert p_type is PingAction.Params and r_type is PingAction.Result
    assert qualified_dotted_name(p_type) == params_id
    assert qualified_dotted_name(r_type) == result_id


def test_entity_node_links_properties_and_domain_helpers() -> None:
    node = EntityNode(SampleEntity)
    dom_id = qualified_dotted_name(TestDomain)
    host = qualified_dotted_name(SampleEntity)

    assert node.node_type == "Entity"
    assert node.label == "SampleEntity"
    assert node.id == host
    assert node.properties == {"description": "Simple test entity"}
    assert node.links == [
        BaseGraphEdge(link_name="domain", target_id=dom_id),
    ]

    assert EntityNode.get_domain_link(SampleEntity) == BaseGraphEdge(
        link_name="domain",
        target_id=dom_id,
    )
    assert EntityNode._get_all_links(SampleEntity) == node.links
