# tests/examples/model/test_entity_projection_samples.py
"""Example model — ``BaseEntity.schema()`` on demo action ``Result`` (PR-5).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validates registration, Pydantic wire validation, ``NodeGraphCoordinator`` topology
(including ``entity_schema``), and keeps example graph builds healthy.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph.nodes.field_graph_node import FieldGraphNode
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.examples.model.entity_projection_demo.actions.order_wire_preview import (
    ProjectionDemoOrderWirePreviewAction,
)
from aoa.examples.model.entity_projection_demo.entities.projection_demo_core import (
    ProjectionDemoCustomerEntity,
    ProjectionDemoOrderEntity,
)
from aoa.examples.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)


def _coordinator_after_samples() -> object:
    import_sample_registration_modules()
    return build_registered_interchange_coordinator()


def test_sample_result_accepts_valid_order_projection() -> None:
    result_cls = ProjectionDemoOrderWirePreviewAction.Result
    r = result_cls.model_validate({
        "label": "x",
        "order": {"id": "ord-1", "status": "confirmed", "total": 10.0},
    })
    assert r.label == "x"
    assert r.order == {"id": "ord-1", "status": "confirmed", "total": 10.0}


def test_sample_result_rejects_invalid_order_projection() -> None:
    result_cls = ProjectionDemoOrderWirePreviewAction.Result
    with pytest.raises(ValueError, match="wire projection"):
        result_cls.model_validate({"label": "x", "order": {"id": "ord-1", "status": "confirmed"}})


@pytest.mark.asyncio
async def test_sample_action_summary_returns_valid_result() -> None:
    action = ProjectionDemoOrderWirePreviewAction()
    r = await action.preview_order_wire_summary(
        ProjectionDemoOrderWirePreviewAction.Params(label="ping"),
        state=None,
        box=None,
        connections=None,
    )
    assert r.label == "ping"
    assert r.order["id"] == "ord-demo-1"
    assert r.order["status"] == "confirmed"
    assert r.order["total"] == 42.5


def test_coordinator_contains_demo_action_and_entities() -> None:
    coord = _coordinator_after_samples()
    nodes = coord.get_all_nodes()
    action_ids = {
        n.node_id
        for n in nodes
        if n.node_type == "Action"
        and getattr(n.node_obj, "__name__", "") == "ProjectionDemoOrderWirePreviewAction"
    }
    assert action_ids

    entity_ids = {n.node_id for n in nodes if isinstance(n, EntityGraphNode)}
    assert TypeIntrospection.full_qualname(ProjectionDemoCustomerEntity) in entity_ids
    assert TypeIntrospection.full_qualname(ProjectionDemoOrderEntity) in entity_ids


def test_result_schema_field_has_entity_schema_to_order_entity() -> None:
    coord = _coordinator_after_samples()
    result_id = TypeIntrospection.full_qualname(ProjectionDemoOrderWirePreviewAction.Result)
    order_entity_id = TypeIntrospection.full_qualname(ProjectionDemoOrderEntity)

    result_nodes = [n for n in coord.get_all_nodes() if n.node_id == result_id]
    assert len(result_nodes) == 1
    result_node = result_nodes[0]
    order_field_nodes = [
        n
        for n in result_node.get_companion_nodes()
        if isinstance(n, FieldGraphNode) and n.node_obj.field_name == "order"
    ]
    assert len(order_field_nodes) == 1

    views = [e for e in order_field_nodes[0].get_all_edges() if e.edge_name == "entity_schema"]
    assert len(views) == 1
    assert views[0].target_node_id == order_entity_id
