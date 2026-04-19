# tests/scenarios/intents_with_runtime/test_compensate_graph.py
"""Integration: ``@compensate`` with ``GraphCoordinator`` facet graph.

``CompensateIntentInspector`` emits one ``compensator`` vertex per rollback method
(``node_name`` = ``{module}.{Action}:{method_name}``), a merged ``action`` row for
the host class with ``has_compensator`` edges, and keeps the aggregate
``get_snapshot(..., "compensator")`` on that ``action`` (``meta.compensators``).
"""

from __future__ import annotations

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.legacy.core import Core
from tests.scenarios.domain_model.domains import TestDomain


def _compensator_nodes_for(coordinator: GraphCoordinator, action_cls: type) -> list[dict]:
    """``compensator`` facet nodes for ``action_cls`` (filters global graph by ``class_ref``)."""
    return [
        n for n in coordinator.get_nodes_by_type("Compensator")
        if n.get("class_ref") is action_cls
    ]


def _coordinator() -> GraphCoordinator:
    return Core.create_coordinator()


class EmptyParams(BaseParams):
    pass


class EmptyResult(BaseResult):
    pass


@meta(description="Test action with compensator", domain=TestDomain)
@check_roles(NoneRole)
class ActionWithCompensatorAction(BaseAction[EmptyParams, EmptyResult]):

    @regular_aspect("Aspect")
    async def target_aspect(self, params, state, box, connections):
        return {}

    @compensate("target_aspect", "Test compensator")
    async def rollback_compensate(self, params, state_before, state_after,
                                  box, connections, error):
        pass

    @summary_aspect("Summary")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


@meta(description="Test action with compensator and context", domain=TestDomain)
@check_roles(NoneRole)
class ActionWithContextCompensatorAction(BaseAction[EmptyParams, EmptyResult]):

    @regular_aspect("Aspect")
    async def target_aspect(self, params, state, box, connections):
        return {}

    @compensate("target_aspect", "Compensator with context")
    @context_requires(Ctx.User.user_id)
    async def rollback_with_context_compensate(self, params, state_before, state_after,
                                               box, connections, error, ctx):
        pass

    @summary_aspect("Summary")
    async def summary(self, params, state, box, connections):
        return EmptyResult()


class TestCompensatorGraphNodes:
    """Per-method ``compensator`` nodes and hydrated ``facet_rows`` for one action class."""

    def test_compensator_node_created(self) -> None:
        coordinator = _coordinator()
        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        assert len(nodes) == 1
        node = nodes[0]
        assert node["node_type"] == "Compensator"
        expected = BaseIntentInspector._make_host_dependent_node_name(
            ActionWithCompensatorAction, "rollback_compensate",
        )
        assert node["id"] == expected
        row = dict(node["facet_rows"])
        assert row["method_name"] == "rollback_compensate"
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Test compensator"

    def test_get_nodes_by_type_returns_all_compensators(self) -> None:
        coordinator = _coordinator()
        n1 = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        n2 = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(n1) == 1
        assert len(n2) == 1
        names = {n["id"] for n in (n1 + n2)}
        assert BaseIntentInspector._make_host_dependent_node_name(
            ActionWithCompensatorAction, "rollback_compensate",
        ) in names
        assert BaseIntentInspector._make_host_dependent_node_name(
            ActionWithContextCompensatorAction, "rollback_with_context_compensate",
        ) in names

    def test_compensator_node_metadata(self) -> None:
        coordinator = _coordinator()
        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        row = dict(nodes[0]["facet_rows"])
        assert row["method_name"] == "rollback_compensate"
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Test compensator"


class TestCompensatorGraphEdges:
    """``has_compensator`` on facet topology; context keys on per-method ``facet_rows``."""

    def test_has_compensator_edge_exists(self) -> None:
        coordinator = _coordinator()
        assert coordinator.get_snapshot(ActionWithCompensatorAction, "meta") is not None
        cls_nodes = coordinator.get_nodes_for_class(ActionWithCompensatorAction)
        assert any(n.get("node_type") == "Action" for n in cls_nodes)

        g = coordinator.facet_topology_copy()
        action_name = BaseIntentInspector._make_node_name(ActionWithCompensatorAction)
        comp_name = BaseIntentInspector._make_host_dependent_node_name(
            ActionWithCompensatorAction, "rollback_compensate",
        )
        action_idx = next(
            (
                idx for idx in g.node_indices()
                if g[idx].get("node_type") == "Action" and g[idx].get("id") == action_name
            ),
            None,
        )
        assert action_idx is not None
        targets = [
            g[t]["id"]
            for _s, t, ep in g.out_edges(action_idx)
            if isinstance(ep, dict) and ep.get("edge_type") == "has_compensator"
        ]
        assert comp_name in targets

    def test_requires_context_edge_for_compensator(self) -> None:
        coordinator = _coordinator()
        comp_nodes = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(comp_nodes) == 1
        row = dict(comp_nodes[0]["facet_rows"])
        assert row["method_name"] == "rollback_with_context_compensate"
        assert Ctx.User.user_id in row["context_keys"]

    def test_compensator_without_context_no_requires_context_edge(self) -> None:
        coordinator = _coordinator()
        comp_nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        row = dict(comp_nodes[0]["facet_rows"])
        assert row["method_name"] == "rollback_compensate"
        assert row["context_keys"] == frozenset()


class TestCompensatorInDependencyTree:
    """Facets for the action class (``get_nodes_for_class``)."""

    def test_dependency_tree_includes_compensator(self) -> None:
        coordinator = _coordinator()
        facets = {n["node_type"] for n in coordinator.get_nodes_for_class(ActionWithCompensatorAction)}
        assert "Compensator" in facets
        assert "Action" in facets

    def test_dependency_tree_depth_for_compensator_with_context(self) -> None:
        coordinator = _coordinator()
        node = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)[0]
        row = dict(node["facet_rows"])
        assert row["method_name"] == "rollback_with_context_compensate"
        assert Ctx.User.user_id in row["context_keys"]
