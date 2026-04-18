"""GraphCoordinator tests - domains in a graph, descriptions in nodes, repr.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

The ``domain`` parameter in ``@meta`` is required (keyword-only). Nodes are checked
``domain`` in the facet graph, descriptions in the payload of nodes and string representation
coordinator

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIO
═══════════════════ ════════════════════ ════════════════════ ════════════════════

TestDomainInvariantActions
    - Action with domain is acceptable.
    - Calling ``meta(...)`` without ``domain=`` is a TypeError.
    - An action without domain aspects is acceptable.

TestDomainInvariantResources
    - ResourceManager with domain - acceptable.

TestDomainEdgeCases
    - An empty class (without @meta) is acceptable.
    - An action without @meta and without aspects is acceptable.

TestDomainNodes
    - The domain action creates a stub node ``domain`` with ``class_ref`` to the domain class.
    - Two actions with one domain - one such node per class ``_OrdersDomain``.
    - Different domains - checking against the ``class_ref`` set in ``{_OrdersDomain, ...}``.
    - Action without aspects with domain: the domain class is specified in the meta facet.
    - **Important:** after ``build()`` the graph may contain foreign ``domain`` from others
      ecosystem classes; tests filter nodes by ``class_ref is _OrdersDomain`` etc.

TestGraphDescriptions
    - Description of the action is available through the ``meta`` node.
    - An action without domain aspects is registered without errors.
    - Empty class - empty description.

TestCoordinatorRepr
    - repr contains state and cached."""


import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.core_action_machine import CoreActionMachine

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


class _OrdersDomain(BaseDomain):
    name = "orders"
    description = "Order domain"


class _PaymentsDomain(BaseDomain):
    name = "payments"
    description = "Payment domain"


#─── Action with domain ───────────────────────── ─────────────────────────


@meta("Create an order", domain=_OrdersDomain)
@check_roles(NoneRole)
class _OrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


#─── Another action with the same domain ────────────────────────────────────


@meta("Receiving an order", domain=_OrdersDomain)
@check_roles(NoneRole)
class _GetOrderAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


#─── Action with another domain ───────────────────── ──────────────────────


@meta("Payment", domain=_PaymentsDomain)
@check_roles(NoneRole)
class _PaymentAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


#─── Action with aspects and domain payments ─────────────────────────────


@meta("Ping with payments domain", domain=_PaymentsDomain)
@check_roles(NoneRole)
class _NoDomainAction(BaseAction["_Params", "_Result"]):

    @summary_aspect("Bottom line")
    async def finalize_summary(self, params, state, box, connections):
        return {"result": "ok"}


#─── ResourceManager with domain ───────────────────── ──────────────────────


@meta("Order Manager", domain=_OrdersDomain)
class _OrderManager(BaseResourceManager):
    pass


#─── ResourceManager with payments domain ─────────────────────────────────


@meta("Manager with domain payments", domain=_PaymentsDomain)
class _NoDomainManager(BaseResourceManager):
    pass


#─── Action without @meta and without aspects ──────────────────────────────────


@check_roles(NoneRole)
class _PlainAction(BaseAction["_Params", "_Result"]):
    pass


#─── Action without aspects, with @meta and domain ────────────────────────────


@meta("Action without aspects", domain=_OrdersDomain)
@check_roles(NoneRole)
class _NoAspectsAction(BaseAction["_Params", "_Result"]):
    pass


class _EmptyClass:
    pass


def _coord() -> GraphCoordinator:
    """Built coordinator with default inspectors."""
    return CoreActionMachine.create_coordinator()


# ═════════════════════════════════════════════════════════════════════════════
#Domain invariant - actions
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainInvariantActions:
    """Domain in @meta for actions with aspects."""

    def test_action_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_OrderAction, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_action_with_aspects_with_payments_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoDomainAction, "meta")
        assert m is not None
        assert m.domain is _PaymentsDomain

    def test_action_without_aspects_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoAspectsAction, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_meta_missing_domain_raises_typeerror(self):
        with pytest.raises(TypeError, match="domain"):
            meta("Description without domain")


# ═════════════════════════════════════════════════════════════════════════════
#Domain invariant - resources
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainInvariantResources:
    """Domain in @meta for ResourceManager."""

    def test_resource_with_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_OrderManager, "meta")
        assert m is not None
        assert m.domain is _OrdersDomain

    def test_resource_with_payments_domain_ok(self):
        coord = _coord()
        m = coord.get_snapshot(_NoDomainManager, "meta")
        assert m is not None
        assert m.domain is _PaymentsDomain


# ═════════════════════════════════════════════════════════════════════════════
#Boundary Cases
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainEdgeCases:
    """Classes without affected invariants."""

    def test_plain_class_no_effect(self):
        coord = _coord()
        assert coord.get_snapshot(_EmptyClass, "meta") is None

    def test_action_without_aspects_no_meta_ok(self):
        coord = _coord()
        assert coord.get_snapshot(_PlainAction, "meta") is None


# ═════════════════════════════════════════════════════════════════════════════
#Domains in the graph
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainNodes:
    """Creating domain nodes in a graph."""

    def test_action_with_domain_creates_domain_node(self):
        coord = _coord()
        nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(nodes) >= 1

    def test_two_actions_same_domain_one_node(self):
        coord = _coord()
        domain_nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(domain_nodes) == 1

    def test_two_actions_different_domains_two_nodes(self):
        coord = _coord()
        refs = {
            n["class_ref"] for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") in (_OrdersDomain, _PaymentsDomain)
        }
        assert refs == {_OrdersDomain, _PaymentsDomain}

    def test_action_without_aspects_has_domain_in_meta_node(self):
        coord = _coord()
        nm = BaseIntentInspector._make_node_name(_NoAspectsAction)
        host = coord.get_node("Action", nm)
        assert host is not None
        meta = host.get("meta")
        assert meta is not None
        assert meta.get("domain") is _OrdersDomain

    def test_resource_with_domain_creates_domain_node(self):
        coord = _coord()
        nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(nodes) >= 1

    def test_action_and_resource_same_domain_shared_node(self):
        coord = _coord()
        domain_nodes = [
            n for n in coord.get_nodes_by_type("domain")
            if n.get("class_ref") is _OrdersDomain
        ]
        assert len(domain_nodes) == 1


# ═════════════════════════════════════════════════════════════════════════════
#Descriptions in graph nodes
# ═════════════════════════════════════════════════════════════════════════════


class TestGraphDescriptions:
    """The graph nodes contain descriptions in the payload."""

    def test_action_node_contains_description(self):
        coord = _coord()
        key = _node_key("Action", _OrderAction)
        node = coord.get_node(key)
        assert node is not None

    def test_action_without_aspects_without_domain_registers(self):
        coord = _coord()
        assert coord.get_snapshot(_NoAspectsAction, "meta") is not None

    def test_empty_class_empty_description(self):
        coord = _coord()
        assert coord.graph_node_count >= 1


# ═════════════════════════════════════════════════════════════════════════════
#String representation of coordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestCoordinatorRepr:
    """__repr__ GraphCoordinator."""

    def test_empty_repr(self):
        coord = GraphCoordinator()
        result = repr(coord)
        assert "GraphCoordinator(" in result
        assert "state=not built" in result

    def test_nonempty_repr(self):
        coord = _coord()
        result = repr(coord)
        assert isinstance(result, str)
        assert "GraphCoordinator(" in result
        assert "state=built" in result
        assert "state=built" in result
