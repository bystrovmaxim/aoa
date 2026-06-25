# tests/action_machine/graph_host/test_parent_generalization_edges.py
"""PR-2: ``parent_*`` generalization edges and factories (plan ``generalization_graph_nodes.md`` §PR-2)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.edge_relationship import GENERALIZATION
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.edges.parent_action_graph_edge import ParentActionGraphEdge, build_parent_action_edges
from aoa.action_machine.graph.edges.parent_domain_graph_edge import ParentDomainGraphEdge, build_parent_domain_edges
from aoa.action_machine.graph.edges.parent_role_graph_edge import ParentRoleGraphEdge, build_parent_role_edges
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from tests.support.domain_model.domains import TestDomain


@meta(description="Parent gen action for PR-2 generalization factory tests", domain=TestDomain)
@check_roles(GuestRole)
class _ParentGenAction(BaseAction["_ParentGenAction.Params", "_ParentGenAction.Result"]):
    """Concrete parent action — not ``@exclude_graph_model`` so it can be a generalization target."""

    class Params(BaseParams):
        pass

    class Result(BaseResult):
        message: str = Field(description="Message")

    @summary_aspect("Summary")
    async def pong_summary(
        self,
        params: _ParentGenAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> _ParentGenAction.Result:
        return self.Result(message="x")


@exclude_graph_model
class _ChildGenAction(_ParentGenAction):
    """Child action with one direct concrete parent action."""


@exclude_graph_model
class _ExcludedParentAction(BaseAction[ParamsStub, ResultStub]):
    """Parent action excluded from graph model — no edge target."""


@exclude_graph_model
class _ChildOfExcludedGenAction(_ExcludedParentAction):
    """When the only direct parent is excluded, factories emit no parent edges."""


@role_mode(RoleMode.ALIVE)
class _ParentGenRole(BaseRole):
    name = "parent_gen_role"
    description = "Parent role for PR-2 tests."


class _ChildGenRole(_ParentGenRole):
    name = "child_gen_role"
    description = "Child role for PR-2 tests."


@role_mode(RoleMode.ALIVE)
class _IntermediateGenRole(BaseRole):
    name = "intermediate_gen_role"
    description = "Intermediate role for exclusion test."


@exclude_graph_model
class _ExcludedFromGraphIntermediateRole(_IntermediateGenRole):
    """Excluded intermediate — edge to this parent must not be built."""


class _ChildOfExcludedIntermediateRole(_ExcludedFromGraphIntermediateRole):
    name = "child_of_excluded_intermediate_role"
    description = "Child whose direct parent is excluded from graph model."


class _ParentGenDomain(BaseDomain):
    name = "parent_gen_domain"
    description = "Parent domain for PR-2 tests."


class _ChildGenDomain(_ParentGenDomain):
    name = "child_gen_domain"
    description = "Child domain for PR-2 tests."


class _IntermediateGenDomain(BaseDomain):
    name = "intermediate_gen_domain"
    description = "Intermediate domain for exclusion test."


@exclude_graph_model
class _ExcludedFromGraphIntermediateDomain(_IntermediateGenDomain):
    """Excluded intermediate domain — edge to this parent must not be built."""


class _ChildOfExcludedIntermediateDomain(_ExcludedFromGraphIntermediateDomain):
    name = "child_of_excluded_intermediate_domain"
    description = "Child whose direct parent domain is excluded from graph model."


def test_build_parent_action_edges_emits_parent_action() -> None:
    edges = build_parent_action_edges(_ChildGenAction)
    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, ParentActionGraphEdge)
    assert edge.edge_name == "parent_action"
    assert edge.edge_relationship is GENERALIZATION
    assert edge.target_node_id == TypeIntrospection.full_qualname(_ParentGenAction)
    d = edge.to_dict(source_id=TypeIntrospection.full_qualname(_ChildGenAction))
    assert d["type"] == "parent_action"
    assert d["relationship"] == GENERALIZATION.archimate_name


def test_build_parent_action_edges_skips_excluded_parent() -> None:
    assert build_parent_action_edges(_ChildOfExcludedGenAction) == []


def test_build_parent_role_edges_emits_parent_role() -> None:
    edges = build_parent_role_edges(_ChildGenRole)
    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, ParentRoleGraphEdge)
    assert edge.edge_name == "parent_role"
    assert edge.target_node_id == TypeIntrospection.full_qualname(_ParentGenRole)


def test_build_parent_role_edges_skips_excluded_parent() -> None:
    assert build_parent_role_edges(_ChildOfExcludedIntermediateRole) == []


def test_build_parent_domain_edges_emits_parent_domain() -> None:
    edges = build_parent_domain_edges(_ChildGenDomain)
    assert len(edges) == 1
    edge = edges[0]
    assert isinstance(edge, ParentDomainGraphEdge)
    assert edge.edge_name == "parent_domain"
    assert edge.target_node_id == TypeIntrospection.full_qualname(_ParentGenDomain)


def test_build_parent_domain_edges_skips_excluded_parent() -> None:
    assert build_parent_domain_edges(_ChildOfExcludedIntermediateDomain) == []


def test_build_parent_action_edges_empty_for_root_chain() -> None:
    @exclude_graph_model
    class _OnlyBaseActionSubclassAction(BaseAction[ParamsStub, ResultStub]):
        pass

    assert build_parent_action_edges(_OnlyBaseActionSubclassAction) == []
