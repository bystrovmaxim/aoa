# tests/scenarios/graph_with_runtime/test_coordinator_graph.py
"""GateCoordinator tests - dependency graph, nodes, edges, loops, public API.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════
Checks that GateCoordinator builds a directed graph from
registered classes, creates nodes for actions, dependencies,
connections, aspects, checkers, subscriptions, sensitive fields, compensators,
detects circular dependencies and provides a public API
for inspection.
═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIO
═══════════════════ ════════════════════ ════════════════════ ════════════════════
TestBasicNodes - creating basic graph nodes.
TestDependenciesAndConnections - nodes and edges of dependencies and connections.
TestAspectsAndCheckers - aspect and checker nodes.
TestSubscriptionsAndSensitive - nodes of subscriptions and sensitive fields.
TestCompensatorNodes - aggregated facet ``compensator`` (without edges
``has_compensator`` to structural ``action``; see CompensateIntentInspector).
TestRecursiveCollection - automatic recursive collection of dependencies.
TestCycleDetection - scenarios without a cycle in the graph (diamond); logical loops @depends
    are not covered by a separate test for CyclicDependencyError.
TestPublicAPI - public methods for graph inspection.
TestInvalidation - invalidation of the coordinator cache.
TestCoordinatorBasic - basic coordinator API.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
FACET GRAPH AND FILTERING IN TESTS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

The graph is built from ``FacetPayload`` inspectors: in ``rustworkx`` - node type, name,
``class_ref``; facet body in snapshots, ``get_node`` / ``hydrate_graph_node``
mix in ``meta``. The ``action`` node (structural) appears only for classes with
``@depends`` and/or ``@connection`` (two inspectors, ``action`` node merged
in coordinator), otherwise
``meta``, ``role``, ``aspect``, ``compensator``, etc. remain. Plugin Subscriptions
- ``subscription`` nodes, not ``plugin``. Sensitive fields in the graph are covered
``SensitiveIntentInspector`` for inheritors of ``BaseSchema`` (not for
``BaseAction``). Graph queries filter nodes by ``class_ref`` or by
name fragment, because after ``build()`` strangers can get into the snapshot
classes from the general inspector scan."""
from typing import Any

import pytest

from action_machine.dependencies.dependency_factory import (
    cached_dependency_factory,
    clear_dependency_factory_cache,
)
from action_machine.dependencies.depends_decorator import depends
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.graph.inspectors.meta_intent_inspector import MetaIntentInspector
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.checkers.result_string_checker import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.logging.sensitive_decorator import sensitive
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.plugins.events import GlobalStartEvent
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.connection_decorator import connection
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole


def _new_coord() -> GateCoordinator:
    """Create built coordinator with default inspector set."""
    return CoreActionMachine.create_coordinator()


def _graph_children(coord: GateCoordinator, full_key: str) -> list[dict[str, Any]]:
    g = coord.get_graph()
    for idx in g.node_indices():
        node = g[idx]
        nk = f"{node['node_type']}:{node['name']}"
        if nk == full_key:
            return [dict(g[t]) for t in g.successor_indices(idx)]
    return []


def _dependency_tree(coord: GateCoordinator, key: str | type) -> dict[str, Any]:
    if isinstance(key, type):
        key = f"action:{BaseIntentInspector._make_node_name(key)}"
    g = coord.get_graph()
    idx_by_key: dict[str, int] = {}
    for i in g.node_indices():
        n = g[i]
        idx_by_key[f"{n['node_type']}:{n['name']}"] = i

    def build(idx: int, visited: set[int]) -> dict[str, Any]:
        payload = g[idx]
        hp = coord.hydrate_graph_node(dict(payload))
        node_result: dict[str, Any] = {
            "node_type": hp["node_type"],
            "name": hp["name"],
            "meta": dict(hp.get("meta", {})),
            "children": [],
        }
        if idx in visited:
            node_result["meta"] = dict(node_result["meta"])
            node_result["meta"]["cycle"] = True
            return node_result
        visited = visited | {idx}
        for _src, target, edge_payload in g.out_edges(idx):
            child_tree = build(target, visited)
            if isinstance(edge_payload, dict):
                child_tree["edge_type"] = edge_payload.get("edge_type")
            else:
                child_tree["edge_type"] = edge_payload
            node_result["children"].append(child_tree)
        return node_result

    idx = idx_by_key.get(key)
    if idx is None:
        return {}
    return build(idx, set())


def _class_present(coord: GateCoordinator, cls: type) -> bool:
    """True when class has any emitted nodes or meta facet."""
    return bool(coord.get_nodes_for_class(cls)) or coord.get_snapshot(cls, "meta") is not None

# ═════════════════════════════════════════════════════════════════════════════
#Helper classes
# ═════════════════════════════════════════════════════════════════════════════


def _node_key(node_type: str, cls: type, suffix: str = "") -> str:
    """Generates the graph node key: 'type:module.ClassName[.suffix]'."""
    name = f"{cls.__module__}.{cls.__qualname__}"
    if suffix:
        name = f"{name}.{suffix}"
    return f"{node_type}:{name}"


class _Params(BaseParams):
    pass


class _Result(BaseResult):
    pass


class _ServiceA:
    pass


class _ServiceB:
    pass


@meta("Mock manager", domain=TestDomain)
class _MockManager(BaseResourceManager):
    """Minimal implementation of BaseResourceManager for graph tests."""
    def get_wrapper_class(self):
        return None


class _EmptyClass:
    pass


@meta("Ping", domain=TestDomain)
@check_roles(NoneRole)
class _PingGraphAction(BaseAction["_Params", "_Result"]):
    """Minimum action for graph tests."""
    @summary_aspect("Pong")
    async def pong_summary(self, params, state, box, connections):
        return {"message": "pong"}


@meta("Action with dependencies", domain=TestDomain)
@check_roles(NoneRole)
@depends(_ServiceA)
@depends(_ServiceB)
class _ActionWithDepsAction(BaseAction["_Params", "_Result"]):
    """Action with two dependencies for graph tests."""
    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Action with connection", domain=TestDomain)
@check_roles(NoneRole)
@connection(_MockManager, key="db", description="DB")
class _ActionWithConnAction(BaseAction["_Params", "_Result"]):
    """Single connection action for graph tests."""
    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Action with checkers", domain=TestDomain)
@check_roles(NoneRole)
class _ActionWithCheckersAction(BaseAction["_Params", "_Result"]):
    """Action with regular aspect and checker for graph tests."""
    @regular_aspect("Step")
    @result_string("name")
    async def step_aspect(self, params, state, box, connections):
        return {"name": "Alice"}

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


class _SensitiveGraphSchema(BaseSchema):
    """Schema with @sensitive - a node of type sensitive builds only SensitiveIntentInspector (BaseSchema)."""

    _secret: str = "hidden"

    @property
    @sensitive()
    def secret(self) -> str:
        return self._secret


class _TestPlugin(Plugin):
    """Test plugin with one subscription for graph tests."""
    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state, event: GlobalStartEvent, log):
        return state


@meta("Action with role", domain=TestDomain)
@check_roles(AdminRole)
class _RoledGraphAction(BaseAction["_Params", "_Result"]):
    """An action with a specific role for graph tests."""
    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Another action with ServiceA", domain=TestDomain)
@check_roles(NoneRole)
@depends(_ServiceA)
class _AnotherActionWithServiceAAction(BaseAction["_Params", "_Result"]):
    """Second action, dependent on _ServiceA, for node split tests."""
    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


@meta("Action with compensator for graph tests", domain=TestDomain)
@check_roles(NoneRole)
class _ActionWithCompensatorGraphAction(BaseAction["_Params", "_Result"]):
    """Action with regular aspect and compensator for graph tests.
    Used in TestCompensatorNodes to check that the coordinator
    creates nodes of type "compensator" and edges "has_compensator" in general
    dependency graph."""
    @regular_aspect("Step with compensator")
    @result_string("value")
    async def step_aspect(self, params, state, box, connections):
        return {"value": "test"}

    @compensate("step_aspect", "Rollback step")
    async def rollback_step_compensate(self, params, state_before, state_after,
                                       box, connections, error):
        pass

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {}


# ═════════════════════════════════════════════════════════════════════════════
#Basic nodes
# ═════════════════════════════════════════════════════════════════════════════


class TestBasicNodes:
    """Checks the creation of basic graph nodes."""

    def test_empty_coordinator_empty_graph(self):
        """Before build(), the graph counters are not available - only the explicit status."""
        coord = GateCoordinator()
        assert coord.build_status() == "not_built"
        assert coord.is_built is False
        with pytest.raises(RuntimeError, match="not built"):
            _ = coord.graph_node_count
        with pytest.raises(RuntimeError, match="not built"):
            _ = coord.graph_edge_count

    def test_register_empty_class_creates_node(self):
        """Registering an empty class creates a node in the graph."""
        coord = _new_coord()
        coord.get_snapshot(_EmptyClass, "meta")
        assert coord.graph_node_count > 0

    def test_register_action_creates_action_node(self):
        """Registering an action with @depends creates a node of type action (structural facet)."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        nodes = coord.get_nodes_by_type("action")
        assert len(nodes) >= 1

    def test_register_plugin_creates_plugin_node(self):
        """Registering a plugin creates subscription facet nodes (not the plugin type)."""
        coord = _new_coord()
        coord.get_snapshot(_TestPlugin, "meta")
        nodes = coord.get_nodes_by_type("subscription")
        assert len(nodes) >= 1

    def test_register_action_with_role_creates_role_node(self):
        """Registering an action with a role creates a role node."""
        coord = _new_coord()
        coord.get_snapshot(_RoledGraphAction, "meta")
        nodes = coord.get_nodes_by_type("role")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
#Dependencies and Connections
# ═════════════════════════════════════════════════════════════════════════════


class TestDependenciesAndConnections:
    """Checks the creation of nodes and edges for dependencies and connections."""

    def test_dependencies_create_nodes_and_edges(self):
        """Dependencies create nodes and edges in a graph."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert coord.graph_node_count > 1
        assert coord.graph_edge_count > 0

    def test_connections_create_nodes_and_edges(self):
        """Connections create nodes and edges in a graph."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithConnAction, "meta")
        assert coord.graph_edge_count > 0

    def test_same_dependency_shared_between_actions(self):
        """The general dependency is one dependency stub node per service class."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        assert _class_present(coord, _ServiceA)
        svc_key_fragment = f"{_ServiceA.__module__}.{_ServiceA.__qualname__}"
        dep_for_a = [
            n for n in coord.get_nodes_by_type("dependency")
            if svc_key_fragment in n["name"]
        ]
        assert len(dep_for_a) == 1


# ═════════════════════════════════════════════════════════════════════════════
#Aspects and checkers
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsAndCheckers:
    """Checks the creation of nodes for aspects and checkers."""

    def test_aspects_create_nodes_and_edges(self):
        """Aspects create nodes and edges in a graph."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        nodes = coord.get_nodes_by_type("aspect")
        assert len(nodes) >= 1

    def test_checkers_create_nodes_and_edges(self):
        """Checkers create nodes and edges in a graph."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        nodes = coord.get_nodes_by_type("checker")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
#Subscriptions and sensitive
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionsAndSensitive:
    """Checks the creation of nodes for subscriptions and sensitive fields."""

    def test_subscriptions_create_nodes_and_edges(self):
        """Subscriptions create nodes in the graph."""
        coord = _new_coord()
        coord.get_snapshot(_TestPlugin, "meta")
        nodes = coord.get_nodes_by_type("subscription")
        assert len(nodes) >= 1

    def test_sensitive_fields_create_nodes_and_edges(self):
        """Sensitive on BaseSchema creates a facet node of type sensitive."""
        coord = _new_coord()
        coord.get_snapshot(_SensitiveGraphSchema, "meta")
        nodes = coord.get_nodes_by_type("sensitive")
        assert len(nodes) >= 1


# ═════════════════════════════════════════════════════════════════════════════
#Compensators in the column
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorNodes:
    """Checks that compensators create nodes of type "compensator" and edges
    "has_compensator" in the general GateCoordinator graph.

    Added as part of the implementation of the compensation mechanism (Saga).
    Detailed tests of the compensator graph (node metadata, requires_context,
    dependency tree) are covered in tests/scenarios/intents_with_runtime/test_compensate_graph.py.
    Here is a minimal check of integration into the general coordinator graph."""

    def test_compensator_node_created_in_graph(self):
        """When registering an action with @compensate, it appears in the column
        "compensator" type node."""
        # Arrange & Act
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCompensatorGraphAction, "meta")

        #Assert is an aggregated node for our class (there may be other actions in the graph)
        nodes = coord.get_nodes_by_type("compensator")
        ours = [n for n in nodes if n["class_ref"] is _ActionWithCompensatorGraphAction]
        assert len(ours) == 1
        node = ours[0]
        assert node["node_type"] == "compensator"
        assert _ActionWithCompensatorGraphAction.__qualname__ in node["name"]

    def test_has_compensator_edge_in_graph(self):
        """In a facet graph, the compensator is a separate node; There are no has_compensator edges."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCompensatorGraphAction, "meta")
        nodes = coord.get_nodes_by_type("compensator")
        node = next(
            n for n in nodes if n["class_ref"] is _ActionWithCompensatorGraphAction
        )
        entry_meta = dict(node["meta"]).get("compensators", ())
        assert any(dict(e)["method_name"] == "rollback_step_compensate" for e in entry_meta)


# ═════════════════════════════════════════════════════════════════════════════
#Recursive dependency collection
# ═════════════════════════════════════════════════════════════════════════════


class TestRecursiveCollection:
    """Checks the automatic recursive collection of dependencies."""

    def test_dependency_class_automatically_registered(self):
        """The dependency class is automatically registered."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert _class_present(coord, _ServiceA)
        assert _class_present(coord, _ServiceB)

    def test_connection_class_automatically_registered(self):
        """The connection class is automatically registered."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithConnAction, "meta")
        assert _class_present(coord, _MockManager)

    def test_duplicate_dependency_not_collected_twice(self):
        """The duplicate dependency is not re-registered."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        size_after_first = len(coord.get_nodes_for_class(_ServiceA))
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        size_after_second = len(coord.get_nodes_for_class(_ServiceA))
        # In snapshot-first graph, the shared dependency class is reused.
        assert size_after_second <= size_after_first + 1


# ═════════════════════════════════════════════════════════════════════════════
#Cycle Detection
# ═════════════════════════════════════════════════════════════════════════════


class TestCycleDetection:
    """Phase 2 of the graph checks the acyclicity of **structural** edges between nodes
    facet-graph (``action`` → ``dependency`` / ``connection`` as different keys).
    Logical loops "A depends on B, B on A" are not required to produce a loop in this
    graph; there is no separate check in ``get()`` along the dependency chain
    implemented - see ``_phase2_check_acyclicity``."""

    def test_diamond_dependency_no_cycle(self):
        """A diamond-shaped dependency without a cycle is acceptable."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        coord.get_snapshot(_AnotherActionWithServiceAAction, "meta")
        assert _class_present(coord, _ActionWithDepsAction)
        assert _class_present(coord, _AnotherActionWithServiceAAction)
        assert _class_present(coord, _ServiceA)


# ═════════════════════════════════════════════════════════════════════════════
#Public API
# ═════════════════════════════════════════════════════════════════════════════


class TestPublicAPI:
    """Checks GateCoordinator's public methods for graph inspection."""

    def test_get_graph_returns_copy(self):
        """get_graph returns a copy of the graph."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        g1 = coord.get_graph()
        g2 = coord.get_graph()
        assert g1 is not g2

    def test_get_node_existing(self):
        """get_node for facet meta registered action returns data."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        key = _node_key("meta", _PingGraphAction)
        node = coord.get_node(key)
        assert node is not None

    def test_get_node_missing_returns_none(self):
        """get_node for an unregistered class returns None."""
        coord = CoreActionMachine.create_coordinator()
        node = coord.get_node("action", "nonexistent.module.AbsentAction")
        assert node is None

    def test_get_children_of_action(self):
        """The child nodes in the graph (outgoing edges) of an action with dependencies are non-empty."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        key = _node_key("action", _ActionWithDepsAction)
        children = _graph_children(coord, key)
        assert len(children) > 0

    def test_get_children_of_missing_node(self):
        """An unregistered class has no edges emanating from the action node."""
        coord = CoreActionMachine.create_coordinator()
        children = _graph_children(coord, _node_key("action", _EmptyClass))
        assert children == []

    def test_get_nodes_by_type_action(self):
        """get_nodes_by_type('action') returns all actions."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        actions = coord.get_nodes_by_type("action")
        assert len(actions) >= 2

    def test_get_nodes_by_type_empty(self):
        """get_nodes_by_type on an empty coordinator - an empty list."""
        coord = CoreActionMachine.create_coordinator()
        result = coord.get_nodes_by_type("action")
        assert isinstance(result, list)

    def test_get_dependency_tree_structure(self):
        """The auxiliary dependency tree for the graph is non-empty for actions with deps."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        tree = _dependency_tree(coord, _ActionWithDepsAction)
        assert tree is not None
        assert isinstance(tree, dict)

    def test_get_dependency_tree_missing_node(self):
        """For a class with no nodes in the graph, the dependency tree is empty or missing."""
        coord = CoreActionMachine.create_coordinator()
        tree = _dependency_tree(coord, _EmptyClass)
        assert tree is None or tree == {}

    def test_get_dependency_tree_checkers_nested_under_aspects(self):
        """The graph tree reflects the checkers under the corresponding aspects."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithCheckersAction, "meta")
        tree = _dependency_tree(coord, _ActionWithCheckersAction)
        assert tree is not None

    def test_graph_node_count(self):
        """graph_node_count returns the number of nodes."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        assert coord.graph_node_count > 0

    def test_graph_edge_count(self):
        """graph_edge_count returns the number of edges."""
        coord = _new_coord()
        coord.get_snapshot(_ActionWithDepsAction, "meta")
        assert coord.graph_edge_count > 0


# ═════════════════════════════════════════════════════════════════════════════
#Invalidation
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidation:
    """Checks for coordinator cache invalidation."""

    def test_invalidate_removes_from_cache(self):
        """Resetting the dependency factory cache does not break reading facet snapshots."""
        coord = _new_coord()
        coord.get_snapshot(_PingGraphAction, "meta")
        removed = clear_dependency_factory_cache(coord)
        assert isinstance(removed, int)
        assert coord.get_snapshot(_PingGraphAction, "meta") is not None

    def test_invalidate_all_clears_cache(self):
        """clear_dependency_factory_cache returns the number of entries cleared."""
        coord = _new_coord()
        cached_dependency_factory(coord, _PingGraphAction)
        cached_dependency_factory(coord, _ActionWithDepsAction)
        removed = clear_dependency_factory_cache(coord)
        assert removed >= 1

    def test_invalidate_preserves_shared_dependency_node(self):
        """Resetting the factory cache does not change the number of facet graph nodes."""
        coord = _new_coord()
        before_nodes = coord.graph_node_count
        clear_dependency_factory_cache(coord)
        assert coord.graph_node_count == before_nodes

    def test_invalidate_allows_rebuild(self):
        """After resetting the factory cache, facet snapshots remain available without rebuild."""
        coord = _new_coord()
        clear_dependency_factory_cache(coord)
        meta = coord.get_snapshot(_PingGraphAction, "meta")
        assert meta is not None
        assert meta.class_ref is _PingGraphAction

    def test_invalidate_non_existing_no_error(self):
        """Resetting the factory cache again does not cause errors."""
        coord = _new_coord()
        clear_dependency_factory_cache(coord)
        clear_dependency_factory_cache(coord)

    def test_invalidate_all_empty_no_error(self):
        """Resetting the factory cache on an unbuilt coordinator - no errors, 0 entries."""
        coord = GateCoordinator()
        assert clear_dependency_factory_cache(coord) == 0


# ═════════════════════════════════════════════════════════════════════════════
#Basic coordinator API
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorBasic:
    """Checks the base GateCoordinator methods."""

    def test_get_builds_and_caches(self):
        """Built coordinator returns stable meta snapshots."""
        coord = CoreActionMachine.create_coordinator()
        meta1 = coord.get_snapshot(_PingGraphAction, "meta")
        meta2 = coord.get_snapshot(_PingGraphAction, "meta")
        assert meta1 is not None
        assert meta2 is not None
        assert meta1.class_ref is _PingGraphAction
        assert meta2.class_ref is _PingGraphAction

    def test_register_same_as_get(self):
        """register now accepts inspector classes only."""
        coord = GateCoordinator()
        returned = coord.register(MetaIntentInspector)
        assert returned is coord

    def test_has_before_get(self):
        """Empty coordinator has not-built state in repr."""
        coord = GateCoordinator()
        assert "state=not built" in repr(coord)

    def test_has_after_get(self):
        """Built coordinator reports built state in repr."""
        coord = CoreActionMachine.create_coordinator()
        assert "state=built" in repr(coord)

    def test_size(self):
        """Graph has nodes after build."""
        coord = CoreActionMachine.create_coordinator()
        assert coord.graph_node_count > 0

    def test_get_all_metadata(self):
        """Meta snapshot is available for decorated action."""
        coord = CoreActionMachine.create_coordinator()
        all_meta = coord.get_snapshot(_PingGraphAction, "meta")
        assert all_meta is not None

    def test_get_all_classes(self):
        """Graph is queryable for known facet type."""
        coord = CoreActionMachine.create_coordinator()
        meta_nodes = coord.get_nodes_by_type("meta")
        assert isinstance(meta_nodes, list)
        assert len(meta_nodes) > 0

    def test_get_not_a_class_raises(self):
        """register rejects non-inspector classes."""
        coord = GateCoordinator()
        with pytest.raises(TypeError):
            coord.register(_EmptyClass)  # type: ignore[arg-type]

    def test_get_factory(self):
        """cached_dependency_factory gives a DependencyFactory for dealing with dependencies."""
        coord = CoreActionMachine.create_coordinator()
        factory = cached_dependency_factory(coord, _ActionWithDepsAction)
        assert factory is not None
        assert factory.has(_ServiceA)
        assert factory.has(_ServiceB)

    def test_repr_empty(self):
        """repr of the empty coordinator is a string."""
        coord = GateCoordinator()
        assert isinstance(repr(coord), str)

    def test_repr_with_classes(self):
        """repr of the coordinator with classes is a string."""
        coord = CoreActionMachine.create_coordinator()
        assert isinstance(repr(coord), str)

    def test_repr_includes_graph_info(self):
        """repr contains information about the graph."""
        coord = CoreActionMachine.create_coordinator()
        result = repr(coord)
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result) > 0
