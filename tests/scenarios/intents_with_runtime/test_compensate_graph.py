# tests/scenarios/intents_with_runtime/test_compensate_graph.py
"""Integration of compensators (@compensate) with the GateCoordinator facet graph.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks how ``CompensateIntentInspector`` fits into a single model
facets: **one** ``compensator`` node per ``BaseAction`` class, regardless of
number of rollback methods. The node name is ``module.QualName`` of the **action class**, not
method name; details for each compensator - in ``meta.compensators`` as
tuple of records - each record ``tuple[tuple[str, Any], ...]`` (key/value pairs,
like ``_make_meta``): ``method_name``, ``target_aspect_name``, ``description``,
``method_ref``, ``context_keys``.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
ARCHITECTURAL SOLUTION (why there is no has_compensator in the tree)
═══════════════════ ════════════════════ ════════════════════ ════════════════════

In the old visualization of the coordinator between the ``action`` node and the ``compensator``
the edge ``has_compensator`` was drawn, and the contextual requirements were drawn separately
edges to ``context_field``. In a facet assembly **ribs from the payload compensator
are empty** (``edges=()``): the "this class contains compensators" relationship is expressed
the fact that there is a node with the same ``class_ref``, and ``@context_requires`` on the method
rollback is reflected **inside** the ``context_keys`` field of the record, without a separate subgraph
context. This simplifies committing the graph and eliminates duplication with runtime metadata.
where the same data is already available for the saga machine.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURAL UNIT action AND TESTS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

The inspectors for ``@depends`` and ``@connection`` spawn a single ``action`` node
(after merging in the coordinator), but only if these declarations are present.
Test actions in this file **without**
dependencies and connections therefore **not** create structural ``action``; instead of
"edge action→compensator" checks consistency between ``meta`` and ``compensator``
for one ``class_ref``, as well as a set of facet types via
``get_nodes_for_class``.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
STRUCTURE OF TEST CLASSES
═══════════════════ ════════════════════ ════════════════════ ════════════════════

TestCompensatorGraphNodes - correctness of one ``compensator`` node and fields
    ``meta.compensators``; filtering by ``class_ref`` (global graph).

TestCompensatorGraphEdges - consistency between facet ``meta`` and ``compensator``;
    context on rollback with ``@context_requires`` vs empty frozenset.

TestCompensatorInDependencyTree - historical class name; actually check
    sets ``node_type`` in ``get_nodes_for_class`` (class facets)."""

from __future__ import annotations

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model.domains import TestDomain

# ═════════════════════════════════════════════════════════════════════════════
#Helper functions and classes
# ═════════════════════════════════════════════════════════════════════════════


def _compensator_nodes_for(coordinator: GateCoordinator, action_cls: type) -> list[dict]:
    """Returns ``compensator`` nodes spawned by a particular action class.

    Required: global ``get_nodes_by_type`` after ``build()`` includes
    compensators for **other** test modules (for example scenarios.domain_model), without
    filter by ``class_ref`` both counters and selection ``nodes[0]`` are incorrect."""
    return [
        n for n in coordinator.get_nodes_by_type("compensator")
        if n.get("class_ref") is action_cls
    ]


def _coordinator() -> GateCoordinator:
    """Return built coordinator with default inspectors."""
    return CoreActionMachine.create_coordinator()


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


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGraphNodes
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGraphNodes:
    """A ``compensator`` node and a ``meta.compensators`` structure for one Action class."""

    def test_compensator_node_created(self) -> None:
        """When registering an action with a compensator, the 'compensator' facet node appears
        to this class with a tuple of compensators in meta."""
        coordinator = _coordinator()

        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        assert len(nodes) == 1

        node = nodes[0]
        assert node["node_type"] == "compensator"
        assert ActionWithCompensatorAction.__qualname__ in node["name"]
        compensators = dict(node["meta"])["compensators"]
        row = dict(next(c for c in compensators if dict(c)["method_name"] == "rollback_compensate"))
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Test compensator"

    def test_get_nodes_by_type_returns_all_compensators(self) -> None:
        """For each of the two actions there is its own compensator unit (unit)."""
        coordinator = _coordinator()

        n1 = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        n2 = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(n1) == 1
        assert len(n2) == 1

        names = [n["name"] for n in (n1 + n2)]
        assert any(ActionWithCompensatorAction.__qualname__ in n for n in names)
        assert any(ActionWithContextCompensatorAction.__qualname__ in n for n in names)

    def test_compensator_node_metadata(self) -> None:
        """meta.compensators stores entries with the keys method_name, target_aspect_name, ..."""
        coordinator = _coordinator()

        nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        meta = dict(nodes[0]["meta"])
        rows = meta["compensators"]
        row = dict(next(r for r in rows if dict(r)["method_name"] == "rollback_compensate"))
        assert row["target_aspect_name"] == "target_aspect"
        assert row["description"] == "Test compensator"


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGraphEdges
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGraphEdges:
    """Consistency of ``meta`` and ``compensator`` facets for the same class.

    Structural ``action`` is missing for actions without ``@depends``/``@connection`` -
    this is expected and is not a regression of compensator integration."""

    def test_has_compensator_edge_exists(self) -> None:
        """For an action there is a facet meta and a facet compensator (action node only for depends/connection)."""
        coordinator = _coordinator()

        meta_nodes = [
            n for n in coordinator.get_nodes_by_type("meta")
            if n.get("class_ref") is ActionWithCompensatorAction
        ]
        assert len(meta_nodes) == 1
        comp_nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        assert len(comp_nodes) == 1

    def test_requires_context_edge_for_compensator(self) -> None:
        """@context_requires keys go into meta.compensators (context_keys field)."""
        coordinator = _coordinator()

        comp_nodes = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)
        assert len(comp_nodes) == 1
        rows: tuple = dict(comp_nodes[0]["meta"])["compensators"]
        row = dict(next(r for r in rows if dict(r)["method_name"] == "rollback_with_context_compensate"))
        assert Ctx.User.user_id in row["context_keys"]

    def test_compensator_without_context_no_requires_context_edge(self) -> None:
        """A compensator without @context_requires has an empty frozenset of context."""
        coordinator = _coordinator()

        comp_nodes = _compensator_nodes_for(coordinator, ActionWithCompensatorAction)
        row = dict(
            next(
                r for r in dict(comp_nodes[0]["meta"])["compensators"]
                if dict(r)["method_name"] == "rollback_compensate"
            ),
        )
        assert row["context_keys"] == frozenset()


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorInDependencyTree
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorInDependencyTree:
    """Facets spawned by the action class (``get_nodes_for_class``).

    The class name is left over from the old “dependency tree” formulation; no check
    calls ``get_dependency_tree``, and records the presence of ``compensator`` and
    ``meta`` among nodes with a common ``class_ref``."""

    def test_dependency_tree_includes_compensator(self) -> None:
        """The registered action has a facet compensator."""
        coordinator = _coordinator()

        facets = {n["node_type"] for n in coordinator.get_nodes_for_class(ActionWithCompensatorAction)}
        assert "compensator" in facets
        assert "meta" in facets

    def test_dependency_tree_depth_for_compensator_with_context(self) -> None:
        """A compensator with context stores keys in meta, without separate edges."""
        coordinator = _coordinator()

        node = _compensator_nodes_for(coordinator, ActionWithContextCompensatorAction)[0]
        row = dict(
            next(
                r for r in dict(node["meta"])["compensators"]
                if dict(r)["method_name"] == "rollback_with_context_compensate"
            ),
        )
        assert Ctx.User.user_id in row["context_keys"]
        assert Ctx.User.user_id in row["context_keys"]
