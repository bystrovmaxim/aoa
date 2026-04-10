"""Extra tests for BaseGateHostInspector helpers."""

from __future__ import annotations

from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector


class _M:
    pass


class _Sub(_M):
    pass


class _SubSub(_Sub):
    pass


def test_base_inspector_helper_methods() -> None:
    node_name = BaseGateHostInspector._make_node_name(_Sub)
    assert _Sub.__qualname__ in node_name
    assert BaseGateHostInspector._make_node_name(_Sub, "x").endswith(".x")

    edge = BaseGateHostInspector._make_edge("m", _Sub, "t", True)
    assert edge.edge_type == "t"
    assert edge.is_structural is True

    edge2 = BaseGateHostInspector._make_edge_by_name("m", "n", "t2", False)
    assert edge2.target_name == "n"
    assert edge2.is_structural is False

    assert BaseGateHostInspector._make_meta(a=1) == (("a", 1),)


def test_base_inspector_collect_subclasses_and_recursive() -> None:
    subs = BaseGateHostInspector._collect_subclasses(_M)
    assert _Sub in subs
    assert _SubSub in subs
    # base implementation should be callable
    assert isinstance(BaseGateHostInspector._subclasses_recursive(), list)
