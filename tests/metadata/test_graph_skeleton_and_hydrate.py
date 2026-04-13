# tests/metadata/test_graph_skeleton_and_hydrate.py
"""
Тесты: узлы ``rx.PyDiGraph`` — только скелет; ``meta`` через снимки и ``hydrate_graph_node``.
"""

from __future__ import annotations

import pytest

import action_machine.graph.gate_coordinator as gc_module
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.domain_model import CompensatedOrderAction, FullAction, TestDbManager
from tests.domain_model.domains import OrdersDomain
from tests.domain_model.services import PaymentService


def test_get_graph_node_payloads_are_skeleton_only() -> None:
    """В копии графа у каждого узла ровно три ключа, без ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    g = coord.get_graph()
    for idx in g.node_indices():
        raw = dict(g[idx])
        assert "meta" not in raw
        assert set(raw.keys()) == {"node_type", "name", "class_ref"}


def test_hydrate_graph_node_restores_meta_from_snapshot() -> None:
    """``hydrate_graph_node`` проецирует тот же ``meta``, что и у ``get_node``."""
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(FullAction)
    g = coord.get_graph()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "meta" and g[i]["name"] == nm
    )
    raw = dict(g[idx])
    hydrated = coord.hydrate_graph_node(raw)
    via_api = coord.get_node("meta", nm)
    assert via_api is not None
    assert hydrated["meta"] == via_api["meta"]
    assert hydrated["meta"]


def test_hydrated_action_node_has_empty_meta() -> None:
    """Узел ``action`` не имеет единого снимка с телом; ``meta`` после гидрации пустой."""
    coord = CoreActionMachine.create_coordinator()
    g = coord.get_graph()
    action_indices = [
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "action" and g[i]["class_ref"] is FullAction
    ]
    assert action_indices, "expected FullAction structural action node"
    raw = dict(g[action_indices[0]])
    assert coord.hydrate_graph_node(raw).get("meta") == {}


def test_hydrate_graph_node_requires_build() -> None:
    """До ``build()`` гидратация запрещена."""
    c = GateCoordinator()
    with pytest.raises(RuntimeError, match="not built"):
        c.hydrate_graph_node({
            "node_type": "meta",
            "name": "x",
            "class_ref": object,
        })


def test_get_nodes_by_type_includes_hydrated_meta() -> None:
    """``get_nodes_by_type`` возвращает записи с непустым ``meta``, когда есть снимок."""
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(FullAction)
    meta_nodes = [n for n in coord.get_nodes_by_type("meta") if n["name"] == nm]
    assert len(meta_nodes) == 1
    assert meta_nodes[0].get("meta")


def test_stub_dependency_node_hydrates_to_empty_meta() -> None:
    """Узлы-заглушки (``dependency``) без снимка дают пустой ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    dep_nodes = [
        n
        for n in coord.get_nodes_by_type("dependency")
        if n.get("class_ref") is PaymentService
    ]
    assert dep_nodes, "expected PaymentService dependency stub in default graph"
    assert dep_nodes[0].get("meta") == {}

    g = coord.get_graph()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "dependency" and g[i]["class_ref"] is PaymentService
    )
    assert coord.hydrate_graph_node(dict(g[idx])).get("meta") == {}


def test_hydration_mapping_from_build_records_meta_snapshot_key() -> None:
    """Phase 1 записывает ключ снимка для гидратации (не статический словарь)."""
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(FullAction)
    gk_meta = f"meta:{nm}"
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert raw_map.get(gk_meta) == "meta"


def test_merged_action_node_marks_hydration_ambiguous() -> None:
    """Слитый structural ``action`` с @depends и @connection даёт конфликт ключей снимка."""
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(FullAction)
    gk_action = f"action:{nm}"
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert raw_map[gk_action] is gc_module._AMBIGUOUS_HYDRATION_KEY


def test_stub_connection_node_hydrates_to_empty_meta() -> None:
    """Заглушка ``connection`` (менеджер из @connection) без снимка — пустой ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    conn_nodes = [
        n
        for n in coord.get_nodes_by_type("connection")
        if n.get("class_ref") is TestDbManager
    ]
    assert conn_nodes, "expected TestDbManager connection stub (e.g. from FullAction)"
    assert conn_nodes[0].get("meta") == {}

    g = coord.get_graph()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "connection" and g[i]["class_ref"] is TestDbManager
    )
    assert coord.hydrate_graph_node(dict(g[idx])).get("meta") == {}


def test_stub_domain_node_hydrates_to_empty_meta() -> None:
    """Узел ``domain`` (класс домена) без facet-снимка — пустой ``meta``."""
    coord = CoreActionMachine.create_coordinator()
    dom_nodes = [
        n
        for n in coord.get_nodes_by_type("domain")
        if n.get("class_ref") is OrdersDomain
    ]
    assert dom_nodes, "expected OrdersDomain node from @meta(domain=...)"
    assert dom_nodes[0].get("meta") == {}

    g = coord.get_graph()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "domain" and g[i]["class_ref"] is OrdersDomain
    )
    assert coord.hydrate_graph_node(dict(g[idx])).get("meta") == {}


def test_action_depends_only_has_single_hydration_key_not_ambiguous() -> None:
    """
    Только @depends (без @connection): один ключ снимка ``depends``, не ambiguous.

    Тело ``meta`` на structural ``action`` по-прежнему пустое (payload без node_meta).
    """
    coord = CoreActionMachine.create_coordinator()
    nm = BaseIntentInspector._make_node_name(CompensatedOrderAction)
    gk = f"action:{nm}"
    raw_map = coord._hydration_snapshot_key_by_graph_key
    assert raw_map.get(gk) == "depends"
    assert raw_map[gk] is not gc_module._AMBIGUOUS_HYDRATION_KEY

    g = coord.get_graph()
    idx = next(
        i
        for i in g.node_indices()
        if g[i]["node_type"] == "action" and g[i]["class_ref"] is CompensatedOrderAction
    )
    assert coord.hydrate_graph_node(dict(g[idx])).get("meta") == {}
