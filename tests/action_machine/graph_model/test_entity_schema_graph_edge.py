# tests/action_machine/graph_model/test_entity_schema_graph_edge.py
"""
``EntitySchemaGraphEdge`` / ``entity_schema`` links for ``BaseEntity.schema(...)`` fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PR-4: concrete Field/PropertyField graph nodes emit ``entity_schema`` aggregation edges
to the declared entity class; coordinator referential integrity and JSON-safe properties.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import Field, computed_field
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


class PropertyWireProjectionResult(BaseResult):
    label: str = Field(description="Label")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def order_projection(self) -> SampleEntity.schema(schema=_ORPHAN_WIRE):  # type: ignore[valid-type]
        """Computed property that returns an entity wire projection."""
        return {"id": self.label, "name": "sample"}


class _MissingEntitySchemaRoot:
    """Isolated inspector axis with no subclasses (single synthetic graph row)."""


class _OrphanResultOnlyInspector(BaseGraphNodeInspector[_MissingEntitySchemaRoot]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if cls is not _MissingEntitySchemaRoot:
            return None
        return ResultGraphNode(OrphanWireProjectionResult)


def _field_node_for(host_node: ResultGraphNode | ParamsGraphNode, field_name: str) -> BaseGraphNode[Any]:
    return next(n for n in host_node.get_companion_nodes() if n.node_id.endswith(f":{field_name}"))


def test_field_graph_node_emits_entity_schema_for_projection_field() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    field_node = _field_node_for(node, "order")
    views = [e for e in field_node.get_all_edges() if e.edge_name == "entity_schema"]
    assert len(views) == 1
    edge = views[0]
    assert edge.is_dag is True
    assert edge.target_node_id == TypeIntrospection.full_qualname(SampleEntity)
    assert edge.properties == {}


def test_regular_result_field_has_no_entity_schema() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    field_node = _field_node_for(node, "domain")
    assert [e for e in field_node.get_all_edges() if e.edge_name == "entity_schema"] == []


def test_entity_schema_targets_sample_entity_graph_node() -> None:
    result_node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    entity_node = EntityGraphNode(SampleEntity)
    field_node = _field_node_for(result_node, "order")
    edge = next(e for e in field_node.get_all_edges() if e.edge_name == "entity_schema")
    assert edge.target_node_id == entity_node.node_id


def test_entity_schema_properties_json_serializable() -> None:
    node = ResultGraphNode(EntityProjectionAdapterTestAction.Result)
    field_node = _field_node_for(node, "order")
    for e in field_node.get_all_edges():
        json.dumps(e.properties)


def test_params_graph_node_field_emits_entity_schema() -> None:
    node = ParamsGraphNode(EntityProjectionParamsMcpTestAction.Params)
    field_node = _field_node_for(node, "order")
    views = [e for e in field_node.get_all_edges() if e.edge_name == "entity_schema"]
    assert len(views) == 1
    assert views[0].target_node_id == TypeIntrospection.full_qualname(SampleEntity)


def test_property_graph_node_emits_entity_schema() -> None:
    node = ResultGraphNode(PropertyWireProjectionResult)
    prop_node = next(n for n in node.get_companion_nodes() if n.node_id.endswith(":order_projection"))
    views = [e for e in prop_node.get_all_edges() if e.edge_name == "entity_schema"]
    assert len(views) == 1
    assert views[0].target_node_id == TypeIntrospection.full_qualname(SampleEntity)


def test_default_coordinator_build_with_entity_projection_actions() -> None:
    import tests.action_machine.adapters.entity_projection_adapter_fixtures  # noqa: F401

    coordinator = create_node_graph_coordinator()
    assert len(coordinator.get_all_nodes()) > 0


def test_coordinator_fails_when_entity_schema_target_absent_from_graph() -> None:
    with pytest.raises(InvalidGraphError, match="missing target_node_id"):
        NodeGraphCoordinator().build([_OrphanResultOnlyInspector()])
