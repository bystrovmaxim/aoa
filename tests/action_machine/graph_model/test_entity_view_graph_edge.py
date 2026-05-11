# tests/action_machine/graph_model/test_entity_view_graph_edge.py
"""
``EntityViewGraphEdge`` / ``entity_view`` links for ``BaseEntity.schema(...)`` fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PR-4: Result/Params graph nodes emit ``entity_view`` aggregation edges to the
declared entity class; coordinator referential integrity and JSON-safe properties.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import Field
from tests.action_machine.adapters.entity_projection_adapter_fixtures import (
    EntityProjectionAdapterTestAction,
    EntityProjectionParamsMcpTestAction,
)
from tests.action_machine.scenarios.domain_model.domains import TestDomain
from tests.action_machine.scenarios.domain_model.entities import SampleEntity

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.graph_model.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph_model.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph_model.nodes.params_graph_node import ParamsGraphNode
from aoa.action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.exceptions import InvalidGraphError
from aoa.graph.exclude_graph_model import exclude_graph_model
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator

_ORPHAN_WIRE: dict[str, object] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
    },
    "required": ["id", "name"],
    "additionalProperties": False,
}


@exclude_graph_model
@meta(description="Excluded orphan entity for missing-target graph tests", domain=TestDomain)
@entity(description="Excluded orphan entity", domain=TestDomain)
class OrphanWireEntity(BaseEntity):
    """Present in type hints but omitted from ``EntityGraphNodeInspector`` rows."""

    id: str = Field(description="Identifier")
    name: str = Field(description="Name")
    value: int = Field(description="Value", ge=0)


@exclude_graph_model
class OrphanWireProjectionResult(BaseResult):
    payload: OrphanWireEntity.schema(schema=_ORPHAN_WIRE) = Field(  # type: ignore[valid-type]
        description="Wire projection of excluded entity",
    )


class _MissingEntityViewRoot:
    """Isolated inspector axis with no subclasses (single synthetic graph row)."""


class _OrphanResultOnlyInspector(BaseGraphNodeInspector[_MissingEntityViewRoot]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if cls is not _MissingEntityViewRoot:
            return None
        return ResultGraphNode(OrphanWireProjectionResult)


def test_result_graph_node_emits_entity_view_for_projection_field() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    views = [e for e in node.get_all_edges() if e.edge_name == "entity_view"]
    assert len(views) == 1
    edge = views[0]
    assert edge.is_dag is True
    assert edge.target_node_id == TypeIntrospection.full_qualname(SampleEntity)
    assert edge.properties == {"field_name": "order"}


def test_result_graph_node_domain_field_has_no_entity_view() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    names = {e.properties.get("field_name") for e in node.entity_views}
    assert names == {"order"}


def test_entity_view_targets_sample_entity_graph_node() -> None:
    result_node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    entity_node = EntityGraphNode(SampleEntity)
    edge = next(e for e in result_node.entity_views if e.properties["field_name"] == "order")
    assert edge.target_node_id == entity_node.node_id


def test_entity_view_properties_json_serializable() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    for e in node.entity_views:
        json.dumps(e.properties)


def test_params_graph_node_emits_entity_view() -> None:
    node = ParamsGraphNode(EntityProjectionParamsMcpTestAction.Params)
    assert len(node.entity_views) == 1
    assert node.entity_views[0].properties["field_name"] == "order"
    assert node.entity_views[0].target_node_id == TypeIntrospection.full_qualname(SampleEntity)


def test_default_coordinator_build_with_entity_projection_actions() -> None:
    import tests.action_machine.adapters.entity_projection_adapter_fixtures  # noqa: F401

    coordinator = create_node_graph_coordinator()
    assert len(coordinator.get_all_nodes()) > 0


def test_coordinator_fails_when_entity_view_target_absent_from_graph() -> None:
    with pytest.raises(InvalidGraphError, match="missing target_node_id"):
        NodeGraphCoordinator().build([_OrphanResultOnlyInspector()])
