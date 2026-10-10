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

import pytest

from aoa.action_machine.context import Context, UserInfo
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Refused
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.demo.model.access_cascade.actions import EarlyStopShapeAction, QuestionPathShapeAction
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


# ═════════════════════════════════════════════════════════════════════════════
# US2 — roles draw their own structure: levels and hierarchy
# ═════════════════════════════════════════════════════════════════════════════

_APP_CHAIN = [
    ("CascadeOfficerRole", "CascadeStaffRole"),
    ("CascadeLineLeadRole", "CascadeOfficerRole"),
    ("CascadeTraineeRole", "CascadeLineLeadRole"),
]
_DOMAIN_CHAIN = [("CascadeDomainSpecialistRole", "CascadeDomainRole")]


def _role_node_ids(coordinator: object) -> list[str]:
    return [node.node_id for node in coordinator.get_all_nodes() if getattr(node, "node_type", None) == "Role"]


def _parent_role_links(coordinator: object) -> set[tuple[str, str]]:
    return {
        (source_id.rsplit(".", 1)[-1], target_id.rsplit(".", 1)[-1])
        for source_id, target_id, _edge in coordinator.get_edges_by_type("parent_role")
    }


def test_us2_role_branches_exist() -> None:
    """The three branches — system, application, domain — each carry a role node."""
    suffixes = {node_id.rsplit(".", 1)[-1] for node_id in _role_node_ids(_coordinator())}
    assert "CascadeSystemGateRole" in suffixes
    assert "CascadeStaffRole" in suffixes
    assert "CascadeDomainRole" in suffixes


def test_us2_system_role_edge_shape() -> None:
    """The system branch is reachable through a role edge, so the drawing can show it."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "SystemRoleEdgeShapeAction")
    edges = _check_roles_edges(coordinator, action_id)
    assert len(edges) == 1
    assert edges[0][1].endswith("CascadeSystemGateRole")


def test_us2_application_chain_is_drawn() -> None:
    """The application chain connects its four levels, child to parent."""
    links = _parent_role_links(_coordinator())
    for child, parent in _APP_CHAIN:
        assert (child, parent) in links


def test_us2_domain_chain_is_drawn() -> None:
    """The domain branch connects its two levels, child to parent."""
    links = _parent_role_links(_coordinator())
    for child, parent in _DOMAIN_CHAIN:
        assert (child, parent) in links


# ═════════════════════════════════════════════════════════════════════════════
# US3 — matching and stopping are visible and provable
# ═════════════════════════════════════════════════════════════════════════════


def test_us3_two_path_match_shape() -> None:
    """The two-path operation carries two role edges from different branches."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "TwoPathMatchShapeAction")
    edges = _check_roles_edges(coordinator, action_id)
    assert len(edges) == 2
    targets = {target_id.rsplit(".", 1)[-1] for _, target_id, _edge in edges}
    assert targets == {"CascadeTraineeRole", "CascadeDomainSpecialistRole"}


@pytest.mark.asyncio
async def test_us3_early_stop_probe_untouched() -> None:
    """A caller refused at CHECK_ROLES never reaches the declared object rule."""
    import aoa.demo.model.access_cascade.actions.early_stop_shape_action as early_stop_module

    early_stop_module._PROBE_CALLS["count"] = 0
    import_sample_registration_modules()
    machine = ActionProductMachine(graph_coordinator=build_registered_interchange_coordinator())
    context = Context(user=UserInfo(user_id="early-stop-caller", roles=()))
    with pytest.raises(AccessDenied) as exc_info:
        await machine.run(context, EarlyStopShapeAction(), EarlyStopShapeAction.Params())
    assert exc_info.value.verdict.gate.value == "CHECK_ROLES"
    assert early_stop_module._PROBE_CALLS["count"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# US4 — a refusal can be an answer
# ═════════════════════════════════════════════════════════════════════════════

_QUESTION_LABEL = "Shape: the asked-about operation — the refusal returns as an answer, never an exception"


def test_us4_question_path_label() -> None:
    """The asked-about operation carries its question-path label in the graph."""
    coordinator = _coordinator()
    action_id = _action_node_id(coordinator, "QuestionPathShapeAction")
    node = coordinator.get_node_by_id(action_id)
    assert node.properties["description"] == _QUESTION_LABEL


@pytest.mark.asyncio
async def test_us4_question_path_refusal_is_an_answer() -> None:
    """Asking in advance returns a refusal answer — never an exception — and runs no aspect."""
    import aoa.demo.model.access_cascade.actions.question_path_shape_action as question_module

    question_module._PIPELINE_RUNS["count"] = 0
    import_sample_registration_modules()
    machine = ActionProductMachine(graph_coordinator=build_registered_interchange_coordinator())
    context = Context(user=UserInfo(user_id="asking-caller", roles=()))
    verdict = await machine.check_access_decide(
        context,
        QuestionPathShapeAction,
        QuestionPathShapeAction.Params(),
    )
    assert isinstance(verdict, Refused)
    assert verdict.gate.value == "CHECK_ROLES"
    assert question_module._PIPELINE_RUNS["count"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# US5 — boundary extremes
# ═════════════════════════════════════════════════════════════════════════════


def test_us5_no_inverse_boundary() -> None:
    """The boundary entity carries its one relation with no reverse side."""
    coordinator = _coordinator()
    entity_ids = [
        node.node_id
        for node in coordinator.get_all_nodes()
        if getattr(node, "node_type", None) == "Entity" and node.node_id.endswith(".CascadeBoundaryEntity")
    ]
    assert len(entity_ids) == 1
    entity_id = entity_ids[0]
    relations = [
        (source_id, target_id, edge)
        for source_id, target_id, edge in coordinator.get_edges_by_type("entity_relation")
        if source_id == entity_id
    ]
    assert len(relations) == 1
    assert relations[0][2].properties["field_name"] == "peer_boundary"
    assert relations[0][2].properties["has_inverse"] is False
