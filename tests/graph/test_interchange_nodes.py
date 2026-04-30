# tests/graph/test_interchange_nodes.py
"""Interchange node types: graph_model nodes for params/result/action/domain/entity/aspects/compensators/on_error."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field

from action_machine.context.context_view import ContextView
from action_machine.context.ctx_constants import Ctx
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.domain.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.domain.graph_model.entity_graph_node import EntityGraphNode
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.regular_aspect_intent_resolver import (
    RegularAspectIntentResolver,
)
from action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)
from action_machine.intents.context_requires.context_requires_decorator import (
    context_requires,
)
from action_machine.legacy.application_context_inspector import ApplicationContextInspector
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from action_machine.model.graph_model.compensator_graph_node import CompensatorGraphNode
from action_machine.model.graph_model.edges.params_graph_edge import ParamsGraphEdge
from action_machine.model.graph_model.edges.regular_aspect_graph_edge import (
    RegularAspectGraphEdge,
)
from action_machine.model.graph_model.edges.result_graph_edge import ResultGraphEdge
from action_machine.model.graph_model.edges.summary_aspect_graph_edge import (
    SummaryAspectGraphEdge,
)
from action_machine.model.graph_model.error_handler_graph_node import ErrorHandlerGraphNode
from action_machine.model.graph_model.field_graph_node import FieldGraphNode
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.model.graph_model.required_context_graph_node import (
    RequiredContextGraphNode,
)
from action_machine.model.graph_model.result_graph_node import ResultGraphNode
from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode
from action_machine.resources.base_resource import BaseResource
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.edge_relationship import COMPOSITION
from graph.facet_vertex import FacetVertex
from tests.scenarios.domain_model.child_action import ChildAction
from tests.scenarios.domain_model.compensate_actions import (
    CompensateAndOnErrorAction,
    CompensatedOrderAction,
)
from tests.scenarios.domain_model.entities import SampleEntity, TestDomain
from tests.scenarios.domain_model.full_action import FullAction
from tests.scenarios.domain_model.ping_action import PingAction


def test_regular_aspect_graph_node_interchange_shape() -> None:
    node = RegularAspectGraphNode(ChildAction.process_aspect, ChildAction)
    assert node.node_obj is ChildAction.process_aspect
    assert node.node_type == RegularAspectGraphNode.NODE_TYPE
    assert node.label == "process_aspect"
    assert node.properties == {"description": "Process value"}
    assert node.node_id == f"{TypeIntrospection.full_qualname(ChildAction)}:process_aspect"
    assert len(node.get_companion_nodes()) == 1
    edges = node.get_all_edges()
    assert len(edges) == 1
    assert edges[0].source_node_id == node.node_id
    assert edges[0].target_node_type == CheckerGraphNode.NODE_TYPE


class _AspectCtxProbeParams(BaseParams):
    token: str = Field(default="x")


class _RegularAspectWithCtx(AspectIntent):
    @regular_aspect("Step")
    @context_requires(Ctx.Request.trace_id, Ctx.User.user_id)
    async def step_aspect(
        self,
        params: _AspectCtxProbeParams,
        state: BaseState,
        box: Any,
        connections: dict[str, BaseResource],
        ctx: ContextView,
    ) -> dict[str, str]:
        return {}


def test_regular_aspect_graph_node_materializes_required_context_companions() -> None:
    node = RegularAspectGraphNode(_RegularAspectWithCtx.step_aspect, _RegularAspectWithCtx)
    assert not node.checkers
    assert len(node.required_context) == 2
    assert node.get_required_context_keys() == frozenset(
        {"request.trace_id", "user.user_id"},
    )
    host = TypeIntrospection.full_qualname(_RegularAspectWithCtx)
    assert [e.target_node_type for e in node.required_context] == [
        RequiredContextGraphNode.NODE_TYPE,
        RequiredContextGraphNode.NODE_TYPE,
    ]
    tgts = []
    for e in node.required_context:
        assert e.edge_name == "required_context"
        assert e.target_node is not None
        tgts.append((e.properties["key"], e.target_node.node_id))
    assert sorted(tgts) == [
        ("request.trace_id", f"{host}:step_aspect:reqctx:request.trace_id"),
        ("user.user_id", f"{host}:step_aspect:reqctx:user.user_id"),
    ]
    assert len(node.get_companion_nodes()) == 2
    assert all(isinstance(n, RequiredContextGraphNode) for n in node.get_companion_nodes())


def test_summary_aspect_graph_node_interchange_shape() -> None:
    node = SummaryAspectGraphNode(PingAction.pong_summary, PingAction)
    assert node.node_obj is PingAction.pong_summary
    assert node.node_type == SummaryAspectGraphNode.NODE_TYPE
    assert node.label == "pong_summary"
    assert node.properties == {"description": "Build pong response"}
    assert node.get_all_edges() == []
    assert node.node_id == f"{TypeIntrospection.full_qualname(PingAction)}:pong_summary"


def test_compensator_graph_node_interchange_shape() -> None:
    node = CompensatorGraphNode(CompensatedOrderAction.rollback_charge_compensate, CompensatedOrderAction)
    assert node.node_obj is CompensatedOrderAction.rollback_charge_compensate
    assert node.node_type == CompensatorGraphNode.NODE_TYPE
    assert node.label == "rollback_charge_compensate"
    assert node.properties == {
        "description": "Rollback payment — refund",
        "target_aspect_name": "charge_aspect",
    }
    assert node.get_all_edges() == []
    assert node.node_id == (f"{TypeIntrospection.full_qualname(CompensatedOrderAction)}:rollback_charge_compensate")


def test_error_handler_graph_node_interchange_shape() -> None:
    node = ErrorHandlerGraphNode(CompensateAndOnErrorAction.handle_finalize_on_error, CompensateAndOnErrorAction)
    assert node.node_obj is CompensateAndOnErrorAction.handle_finalize_on_error
    assert node.node_type == ErrorHandlerGraphNode.NODE_TYPE
    assert node.label == "handle_finalize_on_error"
    assert node.properties == {
        "description": "Handle finalize error",
        "exception_types": (ValueError,),
    }
    assert node.get_all_edges() == []
    assert node.node_id == (f"{TypeIntrospection.full_qualname(CompensateAndOnErrorAction)}:handle_finalize_on_error")


def test_params_graph_node_interchange_shape() -> None:
    class PongParams(BaseParams):
        """Minimal params for node tests."""

        token: str = Field(description="Token")

    node = ParamsGraphNode(PongParams)
    assert node.node_obj is PongParams
    assert node.node_type == "Params"
    assert node.label == "PongParams"
    assert node.node_id == TypeIntrospection.full_qualname(PongParams)
    assert node.properties == {}
    assert len(node.get_companion_nodes()) == 1
    edges = node.get_all_edges()
    assert len(edges) == 1
    assert edges[0].edge_name == "field"
    assert edges[0].source_node_id == node.node_id
    assert edges[0].target_node_type == FieldGraphNode.NODE_TYPE
    assert edges[0].edge_relationship is COMPOSITION


def test_result_graph_node_interchange_shape() -> None:
    class PongResult(BaseResult):
        """Minimal result for node tests."""

        ok: bool = Field(description="Ok")

    node = ResultGraphNode(PongResult)
    assert node.node_obj is PongResult
    assert node.node_type == "Result"
    assert node.label == "PongResult"
    assert node.node_id == TypeIntrospection.full_qualname(PongResult)
    assert node.properties == {}
    assert len(node.get_companion_nodes()) == 1
    edges = node.get_all_edges()
    assert len(edges) == 1
    assert edges[0].edge_name == "field"
    assert edges[0].source_node_id == node.node_id
    assert edges[0].target_node_type == FieldGraphNode.NODE_TYPE
    assert edges[0].edge_relationship is COMPOSITION


def test_domain_node_interchange_shape() -> None:
    node = DomainGraphNode(TestDomain)
    assert node.node_obj is TestDomain
    assert node.node_id == TypeIntrospection.full_qualname(TestDomain)
    assert node.node_type == "Domain"
    assert node.node_type == "Domain"
    assert node.label == "TestDomain"
    assert node.node_id == TypeIntrospection.full_qualname(TestDomain)
    assert node.properties == {
        "name": TestDomain.name,
        "description": TestDomain.description,
    }
    assert node.get_all_edges() == []

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
    params_id = TypeIntrospection.full_qualname(PingAction.Params)
    result_id = TypeIntrospection.full_qualname(PingAction.Result)
    host = TypeIntrospection.full_qualname(PingAction)
    summary_node = SummaryAspectGraphNode(
        SummaryAspectIntentResolver.resolve_summary_aspects(PingAction)[0],
        PingAction,
    )

    assert node.node_type == "Action"
    assert node.label == "PingAction"
    assert node.node_id == host
    assert node.get_all_edges() == [
        DomainGraphEdge(
            source_cls=PingAction,
            source_node_type="Action",
            source_node=node,
        ),
        ParamsGraphEdge(PingAction, source_node_type="Action", source_node=node),
        ResultGraphEdge(PingAction, source_node_type="Action", source_node=node),
        SummaryAspectGraphEdge(
            source_node=node,
            summary_node=summary_node,
        ),
    ]

    assert node.domain == DomainGraphEdge(
        source_cls=PingAction,
        source_node_type="Action",
        source_node=node,
    )
    assert node.params == ParamsGraphEdge(
        PingAction,
        source_node_type="Action",
        source_node=node,
    )
    assert node.result == ResultGraphEdge(
        PingAction,
        source_node_type="Action",
        source_node=node,
    )

    p_type = ActionSchemaIntentResolver.resolve_params_type(PingAction)
    r_type = ActionSchemaIntentResolver.resolve_result_type(PingAction)
    assert p_type is PingAction.Params and r_type is PingAction.Result
    assert TypeIntrospection.full_qualname(p_type) == params_id
    assert TypeIntrospection.full_qualname(r_type) == result_id
    assert not node.regular_aspect
    assert node.summary_aspect == [
        SummaryAspectGraphEdge(
            source_node=node,
            summary_node=summary_node,
        ),
    ]
    assert not node.compensator_graph
    assert not node.error_handler_graph
    assert node.get_companion_nodes() == [summary_node]
    assert (
        SummaryAspectGraphEdge(
            source_node=node,
            summary_node=summary_node,
        )
        in node.get_all_edges()
    )


def test_action_graph_node_get_summary_aspect_raises_when_no_summary_edges() -> None:
    node = ActionGraphNode(PingAction)
    object.__setattr__(node, "summary_aspect", [])
    with pytest.raises(ValueError, match="no summary_aspect edges"):
        node.get_summary_aspect_graph_node()


def test_action_graph_node_appends_regular_aspect() -> None:
    node = ActionGraphNode(ChildAction)
    aspect_node = RegularAspectGraphNode(
        RegularAspectIntentResolver.resolve_regular_aspects(ChildAction)[0],
        ChildAction,
    )

    expected_edge = RegularAspectGraphEdge(
        source_node=node,
        aspect_node=aspect_node,
    )
    assert node.regular_aspect == [expected_edge]
    assert aspect_node in node.get_companion_nodes()
    assert aspect_node.get_companion_nodes()[0] in node.get_companion_nodes()
    assert expected_edge in node.get_all_edges()
    assert aspect_node.get_all_edges()[0] not in node.get_all_edges()


def test_action_graph_node_stores_depends_and_connection() -> None:
    node = ActionGraphNode(FullAction)

    assert len(node.depends) == 3
    assert len(node.connection) == 1
    assert all(edge in node.get_all_edges() for edge in node.depends)
    assert all(edge in node.get_all_edges() for edge in node.connection)


def test_compensator_graph_node_for_aspect_matches_target_aspect_properties() -> None:
    """Locator uses CompensatorGraphNode.properties[\"target_aspect_name\"] (facet-aligned)."""
    action_node = ActionGraphNode(CompensatedOrderAction)
    charge = action_node.compensator_graph_node_for_aspect("charge_aspect")
    reserve = action_node.compensator_graph_node_for_aspect("reserve_aspect")
    assert charge is not None
    assert reserve is not None
    assert isinstance(charge, CompensatorGraphNode)
    assert isinstance(reserve, CompensatorGraphNode)
    assert charge.properties["target_aspect_name"] == "charge_aspect"
    assert reserve.properties["target_aspect_name"] == "reserve_aspect"
    assert charge.node_id.endswith(":rollback_charge_compensate")
    assert reserve.node_id.endswith(":rollback_reserve_compensate")
    assert action_node.compensator_graph_node_for_aspect("no_such_aspect") is None


def test_compensator_graph_node_for_aspect_strips_aspect_name() -> None:
    action_node = ActionGraphNode(CompensatedOrderAction)
    found = action_node.compensator_graph_node_for_aspect("  charge_aspect\t")
    assert found is not None
    assert found.label == "rollback_charge_compensate"


def test_compensator_graph_node_for_aspect_none_when_action_has_no_compensators() -> None:
    action_node = ActionGraphNode(PingAction)
    assert action_node.compensator_graph_node_for_aspect("pong_aspect") is None


def test_entity_node_links_properties_and_domain_helpers() -> None:
    node = EntityGraphNode(SampleEntity)
    assert node.node_obj is SampleEntity
    dom_id = TypeIntrospection.full_qualname(TestDomain)
    host = TypeIntrospection.full_qualname(SampleEntity)

    assert node.node_type == "Entity"
    assert node.label == "SampleEntity"
    assert node.node_id == host
    assert node.properties == {"description": "Simple test entity"}
    assert node.domain_edge == AssociationGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id=host,
        source_node_type="Entity",
        source_node=node,
        target_node_id=dom_id,
        target_node_type="Domain",
        target_node=None,
    )
    assert node.get_all_edges() == [
        node.domain_edge,
    ]
