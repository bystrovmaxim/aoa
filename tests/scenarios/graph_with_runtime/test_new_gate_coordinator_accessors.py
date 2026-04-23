# tests/scenarios/graph_with_runtime/test_new_gate_coordinator_accessors.py
"""Tests for runtime accessors on ``GraphCoordinator``."""

from __future__ import annotations

from action_machine.legacy.aspect_intent_inspector import AspectIntentInspector
from action_machine.legacy.checker_intent_inspector import CheckerIntentInspector
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
)
from action_machine.legacy.core import Core
from action_machine.legacy.entity_intent_inspector import EntityIntentInspector
from action_machine.legacy.interchange_vertex_labels import (
    CHECKER_VERTEX_TYPE,
    COMPENSATOR_VERTEX_TYPE,
    ENTITY_VERTEX_TYPE,
    REGULAR_ASPECT_VERTEX_TYPE,
)
from action_machine.legacy.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.resources.base_resource import BaseResource
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex
from graph.graph_coordinator import GraphCoordinator
from tests.scenarios.domain_model import FullAction
from tests.scenarios.domain_model.services import NotificationService, PaymentService


class _DemoEntity:
    pass


class _DemoAction:
    pass


class _DbManagerStub(BaseResource):
    def get_wrapper_class(self):
        return None


def test_new_coordinator_runtime_accessors() -> None:
    coordinator = GraphCoordinator()
    entity_name = BaseIntentInspector._make_node_name(_DemoEntity)
    action_name = BaseIntentInspector._make_node_name(_DemoAction)
    comp_rollback_name = BaseIntentInspector._make_host_dependent_node_name(
        _DemoAction, "rollback_do_compensate",
    )
    rm_name = BaseIntentInspector._make_node_name(_DbManagerStub)
    do_aspect_ref = object()
    summary_ref = object()
    coordinator._phase3_commit(  # pylint: disable=protected-access
        [
            FacetVertex(
                node_type=ENTITY_VERTEX_TYPE,
                node_name=entity_name,
                node_class=_DemoEntity,
                node_meta=(("description", "Demo entity"),),
            ),
            FacetVertex(
                node_type=REGULAR_ASPECT_VERTEX_TYPE,
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    (
                        "aspects",
                        (
                            BaseIntentInspector._make_meta(
                                aspect_type="regular",
                                method_name="do_aspect",
                                description="Do step",
                                method_ref=do_aspect_ref,
                                context_keys=frozenset(),
                            ),
                            BaseIntentInspector._make_meta(
                                aspect_type="summary",
                                method_name="result_summary",
                                description="Make result",
                                method_ref=summary_ref,
                                context_keys=frozenset(),
                            ),
                        ),
                    ),
                ),
            ),
            FacetVertex(
                node_type=CHECKER_VERTEX_TYPE,
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    (
                        "checkers",
                        (
                            BaseIntentInspector._make_meta(
                                method_name="do_aspect",
                                checker_class=object,
                                field_name="value",
                                required=True,
                                extra_params=(),
                            ),
                        ),
                    ),
                ),
            ),
            FacetVertex(
                node_type="error_handler",
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    (
                        "error_handlers",
                        (
                            BaseIntentInspector._make_meta(
                                method_name="handle_value_on_error",
                                exception_types=(ValueError,),
                                description="Handle value error",
                                method_ref=object(),
                                context_keys=frozenset(),
                            ),
                        ),
                    ),
                ),
            ),
            FacetVertex(
                node_type=COMPENSATOR_VERTEX_TYPE,
                node_name=comp_rollback_name,
                node_class=_DemoAction,
                node_meta=BaseIntentInspector._make_meta(
                    method_name="rollback_do_compensate",
                    target_aspect_name="do_aspect",
                    description="Rollback step",
                    method_ref=object(),
                    context_keys=frozenset(),
                ),
            ),
            FacetVertex(
                node_type="resource_manager",
                node_name=rm_name,
                node_class=_DbManagerStub,
                node_meta=(),
                edges=(),
            ),
            FacetVertex(
                node_type="Action",
                node_name=action_name,
                node_class=_DemoAction,
                edges=(
                    FacetEdge(
                        target_node_type="resource_manager",
                        target_name=rm_name,
                        edge_type="connection",
                        is_structural=True,
                        edge_meta=(("description", "primary"), ("key", "db")),
                    ),
                    FacetEdge(
                        target_node_type=COMPENSATOR_VERTEX_TYPE,
                        target_name=comp_rollback_name,
                        edge_type="has_compensator",
                        is_structural=False,
                        target_class_ref=_DemoAction,
                    ),
                ),
            ),
        ]
    )
    # Keep manually seeded graph/snapshots intact: skip lazy auto-build path.
    coordinator._built = True  # pylint: disable=protected-access
    coordinator._facet_snapshots[(_DemoEntity, "entity")] = (  # pylint: disable=protected-access
        EntityIntentInspector.Snapshot(
            class_ref=_DemoEntity,
            entity_info=EntityIntentInspector.Snapshot.EntityInfo(
                description="Demo entity",
            ),
            entity_fields=(),
            entity_relations=(),
            entity_lifecycles=(),
        )
    )
    coordinator._facet_snapshots[(_DemoAction, "aspect")] = (  # pylint: disable=protected-access
        AspectIntentInspector.Snapshot(
            class_ref=_DemoAction,
            aspects=(
                AspectIntentInspector.Snapshot.Aspect(
                    method_name="do_aspect",
                    aspect_type="regular",
                    description="Do step",
                    method_ref=do_aspect_ref,
                    context_keys=frozenset(),
                ),
                AspectIntentInspector.Snapshot.Aspect(
                    method_name="result_summary",
                    aspect_type="summary",
                    description="Make result",
                    method_ref=summary_ref,
                    context_keys=frozenset(),
                ),
            ),
        )
    )
    coordinator._facet_snapshots[(_DemoAction, "checker")] = (  # pylint: disable=protected-access
        CheckerIntentInspector.Snapshot(
            class_ref=_DemoAction,
            checkers=(
                CheckerIntentInspector.Snapshot.Checker(
                    method_name="do_aspect",
                    checker_class=object,
                    field_name="value",
                    required=True,
                    extra_params={},
                ),
            ),
        )
    )
    coordinator._facet_snapshots[(_DemoAction, "error_handler")] = (  # pylint: disable=protected-access
        OnErrorIntentInspector.Snapshot(
            class_ref=_DemoAction,
            error_handlers=(
                OnErrorIntentInspector.Snapshot.ErrorHandler(
                    method_name="handle_value_on_error",
                    exception_types=(ValueError,),
                    description="Handle value error",
                    method_ref=object(),
                    context_keys=frozenset(),
                ),
            ),
        )
    )
    coordinator._facet_snapshots[(_DemoAction, "compensator")] = (  # pylint: disable=protected-access
        CompensateIntentInspector.Snapshot(
            class_ref=_DemoAction,
            compensators=(
                CompensateIntentInspector.Snapshot.Compensator(
                    method_name="rollback_do_compensate",
                    target_aspect_name="do_aspect",
                    description="Rollback step",
                    method_ref=object(),
                    context_keys=frozenset(),
                ),
            ),
        )
    )

    ent_node = coordinator.get_node(ENTITY_VERTEX_TYPE, entity_name)
    assert ent_node is not None
    assert ent_node.get("facet_rows", {}).get("description") == "Demo entity"

    asp = coordinator.get_snapshot(_DemoAction, "aspect")
    assert asp is not None
    regular = tuple(a for a in asp.aspects if a.aspect_type == "regular")
    assert len(regular) == 1
    assert regular[0].method_name == "do_aspect"

    summary = next((a for a in asp.aspects if a.aspect_type == "summary"), None)
    assert summary is not None
    assert summary.method_name == "result_summary"

    ch_snap = coordinator.get_snapshot(_DemoAction, "checker")
    assert ch_snap is not None
    checkers = tuple(c for c in ch_snap.checkers if c.method_name == "do_aspect")
    assert len(checkers) == 1
    assert checkers[0].field_name == "value"

    err = ValueError("x")
    eh_snap = coordinator.get_snapshot(_DemoAction, "error_handler")
    assert eh_snap is not None
    handler = next(
        (
            h
            for h in eh_snap.error_handlers
            if any(isinstance(err, et) for et in h.exception_types)
        ),
        None,
    )
    assert handler is not None
    assert handler.method_name == "handle_value_on_error"

    comp_snap = coordinator.get_snapshot(_DemoAction, "compensator")
    assert comp_snap is not None
    compensator = next(
        (c for c in comp_snap.compensators if c.target_aspect_name == "do_aspect"),
        None,
    )
    assert compensator is not None
    assert compensator.method_name == "rollback_do_compensate"

    g = coordinator.facet_topology_copy()
    action_full = f"Action:{action_name}"
    connection_keys: list[str] = []
    for idx in g.node_indices():
        n = g[idx]
        if f"{n['node_type']}:{n['id']}" != action_full:
            continue
        for _s, _t, ep in g.out_edges(idx):
            if isinstance(ep, dict) and ep.get("edge_type") == "connection":
                ck = ep.get("edge_row", {}).get("key")
                if isinstance(ck, str):
                    connection_keys.append(ck)
    assert tuple(connection_keys) == ("db",)


def test_gate_coordinator_get_graph_for_visualization_matches_get_graph() -> None:
    coordinator = Core.create_coordinator()
    v = coordinator.get_graph_for_visualization()
    lg = coordinator.get_graph()
    assert len(v) == len(lg)
    for idx in v.node_indices():
        assert v[idx] == lg[idx]


def test_coordinator_get_dependency_classes_and_connections() -> None:
    coordinator = Core.create_coordinator()
    deps_snap = coordinator.get_snapshot(FullAction, "depends")
    assert deps_snap is not None
    classes = tuple(d.cls for d in deps_snap.dependencies)
    assert PaymentService in classes
    assert NotificationService in classes
    conn_snap = coordinator.get_snapshot(FullAction, "connections")
    assert conn_snap is not None
    conns = tuple(conn_snap.connections)
    assert len(conns) == 1
    assert conns[0].key == "db"
