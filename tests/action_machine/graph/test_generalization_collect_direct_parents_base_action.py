# tests/action_machine/graph/test_generalization_collect_direct_parents_base_action.py
"""``collect_direct_parents`` against real ``BaseAction`` (cannot live under ``tests/graph`` — import boundary)."""

from __future__ import annotations

from aoa.action_machine.graph.core.generalization_graph_edge import GeneralizationGraphEdge
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub


def test_collect_direct_parents_base_action_axis_parametrized_root_only_yields_empty() -> None:
    """PR-8: ``class C(BaseAction[P, R])`` has no materialized parent except the axis root."""

    class _DirectAction(BaseAction[ParamsStub, ResultStub]):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(_DirectAction, BaseAction) == ()


def test_collect_direct_parents_base_action_axis_mid_and_leaf() -> None:
    """PR-8: real ``BaseAction`` hierarchy — concrete mid action is the direct parent of the leaf."""

    class _MidAction(BaseAction[ParamsStub, ResultStub]):
        pass

    class _LeafAction(_MidAction):
        pass

    assert GeneralizationGraphEdge.collect_direct_parents(_LeafAction, BaseAction) == (_MidAction,)
    assert GeneralizationGraphEdge.collect_direct_parents(_MidAction, BaseAction) == ()
