# tests/metadata/test_new_gate_coordinator_accessors.py
"""Tests for runtime accessors in new metadata GateCoordinator."""

from __future__ import annotations

from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.metadata.payload import EdgeInfo, FacetPayload
from action_machine.on_error.on_error_gate_host_inspector import OnErrorGateHostInspector
from tests.domain_model import FullAction
from tests.domain_model.services import NotificationService, PaymentService


class _DemoEntity:
    pass


class _DemoAction:
    pass


def test_new_coordinator_runtime_accessors() -> None:
    coordinator = GateCoordinator()
    entity_name = BaseGateHostInspector._make_node_name(_DemoEntity)
    action_name = BaseGateHostInspector._make_node_name(_DemoAction)
    do_aspect_ref = object()
    summary_ref = object()
    coordinator._phase3_commit(  # pylint: disable=protected-access
        [
            FacetPayload(
                node_type="entity",
                node_name=entity_name,
                node_class=_DemoEntity,
                node_meta=(("description", "Demo entity"),),
            ),
            FacetPayload(
                node_type="aspect",
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    (
                        "aspects",
                        (
                            ("regular", "do_aspect", "Do step", do_aspect_ref, frozenset()),
                            ("summary", "result_summary", "Make result", summary_ref, frozenset()),
                        ),
                    ),
                ),
            ),
            FacetPayload(
                node_type="checker",
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    ("checkers", (("do_aspect", object, "value", True, ()),)),
                ),
            ),
            FacetPayload(
                node_type="error_handler",
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    (
                        "error_handlers",
                        (("handle_value_on_error", (ValueError,), "Handle value error", object(), frozenset()),),
                    ),
                ),
            ),
            FacetPayload(
                node_type="compensator",
                node_name=action_name,
                node_class=_DemoAction,
                node_meta=(
                    ("compensators", (("rollback_do_compensate", "do_aspect", "Rollback step", object(), frozenset()),)),
                ),
            ),
            FacetPayload(
                node_type="connection",
                node_name="_DbManager",
                node_class=object,
            ),
            FacetPayload(
                node_type="action",
                node_name=action_name,
                node_class=_DemoAction,
                edges=(
                    EdgeInfo(
                        target_node_type="connection",
                        target_name="_DbManager",
                        edge_type="connection",
                        is_structural=True,
                        edge_meta=(("key", "db"), ("description", "primary")),
                    ),
                ),
            ),
        ]
    )
    # Keep manually seeded graph/snapshots intact: skip lazy auto-build path.
    coordinator._built = True  # pylint: disable=protected-access
    coordinator._facet_snapshots[(_DemoAction, "aspect")] = (  # pylint: disable=protected-access
        AspectGateHostInspector.Snapshot(
            class_ref=_DemoAction,
            aspects=(
                AspectGateHostInspector.Snapshot.Aspect(
                    method_name="do_aspect",
                    aspect_type="regular",
                    description="Do step",
                    method_ref=do_aspect_ref,
                    context_keys=frozenset(),
                ),
                AspectGateHostInspector.Snapshot.Aspect(
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
        CheckerGateHostInspector.Snapshot(
            class_ref=_DemoAction,
            checkers=(
                CheckerGateHostInspector.Snapshot.Checker(
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
        OnErrorGateHostInspector.Snapshot(
            class_ref=_DemoAction,
            error_handlers=(
                OnErrorGateHostInspector.Snapshot.ErrorHandler(
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
        CompensateGateHostInspector.Snapshot(
            class_ref=_DemoAction,
            compensators=(
                CompensateGateHostInspector.Snapshot.Compensator(
                    method_name="rollback_do_compensate",
                    target_aspect_name="do_aspect",
                    description="Rollback step",
                    method_ref=object(),
                    context_keys=frozenset(),
                ),
            ),
        )
    )

    ent_node = coordinator.get_node("entity", entity_name)
    assert ent_node is not None
    assert ent_node.get("meta", {}).get("description") == "Demo entity"

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

    g = coordinator.get_graph()
    action_full = f"action:{action_name}"
    connection_keys: list[str] = []
    for idx in g.node_indices():
        n = g[idx]
        if f"{n['node_type']}:{n['name']}" != action_full:
            continue
        for _s, _t, ep in g.out_edges(idx):
            if isinstance(ep, dict) and ep.get("edge_type") == "connection":
                ck = ep.get("meta", {}).get("key")
                if isinstance(ck, str):
                    connection_keys.append(ck)
    assert tuple(connection_keys) == ("db",)


def test_coordinator_get_dependency_classes_and_connections() -> None:
    coordinator = CoreActionMachine.create_coordinator()
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
