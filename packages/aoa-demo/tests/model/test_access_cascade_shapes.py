# packages/aoa-demo/tests/model/test_access_cascade_shapes.py
"""
Access-cascade demonstrator — the fixtures draw every cascade shape.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

After the sample modules register the access-cascade fixtures, the built
interchange graph must carry each declared shape. Test groups are added per
user story, in phase order: US1 (the four cascade-step operations), US2 (the
role branches and chains), US3 (the two matching paths and the early stop),
US4 (the question-path label and the answered refusal), US5 (the NoInverse
boundary).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    import_sample_registration_modules()
        |
        v
    build_registered_interchange_coordinator()
        |
        v
    nodes + @check_roles / @access_decide edges with runtime-only properties
"""

from __future__ import annotations

from aoa.demo.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)

_WHEN_REASON = "shape: WHEN refuses although the role matched"
_GUARD_REASON = "shape: GUARD refuses every caller alike"


def _coordinator() -> object:
    import_sample_registration_modules()
    return build_registered_interchange_coordinator()


def _action_node_id(coordinator: object, class_name: str) -> str:
    for node in coordinator.get_all_nodes():
        if getattr(node, "node_type", None) == "Action" and node.node_id.endswith(f".{class_name}"):
            return node.node_id
    raise AssertionError(f"Action node not found: {class_name}")


def _check_roles_edges(coordinator: object, action_id: str) -> list[tuple[str, str, object]]:
    return [
        (source_id, target_id, edge)
        for source_id, target_id, edge in coordinator.get_edges_by_type("@check_roles")
        if source_id == action_id
    ]


# ═════════════════════════════════════════════════════════════════════════════
# US1 — every cascade step draws as a distinct shape
# ═════════════════════════════════════════════════════════════════════════════


def test_us1_role_check_alone_shape() -> None:
    """The role-check operation carries one role edge and no condition, guard or object rule."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "RoleCheckAloneShapeAction")
    edges = _check_roles_edges(coordinator, action_id)
    assert len(edges) == 1
    assert edges[0][1].endswith("CascadeOfficerRole")
    assert edges[0][2].properties["when"] is None
    assert edges[0][2].properties["when_reason"] is None
    node = coordinator.get_node_by_id(action_id)
    assert node.properties["guard"] is None
    assert node.properties["guard_reason"] is None


def test_us1_when_refusal_shape() -> None:
    """The when-operation carries a grant whose condition refuses although the role matched."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "WhenRefusalShapeAction")
    edges = _check_roles_edges(coordinator, action_id)
    assert len(edges) == 1
    assert edges[0][2].properties["when"] is not None
    assert edges[0][2].properties["when_reason"] == _WHEN_REASON


def test_us1_guard_refusal_shape() -> None:
    """The guard-operation carries a shared guard that refuses for everyone alike."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "GuardRefusalShapeAction")
    edges = _check_roles_edges(coordinator, action_id)
    assert len(edges) == 1
    assert edges[0][2].properties["when"] is None
    node = coordinator.get_node_by_id(action_id)
    assert node.properties["guard"] is not None
    assert node.properties["guard_reason"] == _GUARD_REASON


def test_us1_access_decide_shape() -> None:
    """The object-rule operation carries its declared access-decide edge."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "AccessDecideShapeAction")
    access_edges = [
        (source_id, target_id)
        for source_id, target_id, _edge in coordinator.get_edges_by_type("@access_decide")
        if source_id == action_id
    ]
    assert len(access_edges) == 1
