# packages/aoa-action-machine/tests/action_machine/graph/test_declared_reasons.py
"""
The declared reasons reach the graph, so introspection sees them the way the runtime does.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reason is declared beside a condition, and it belongs to exactly that condition: a
grant's own reason rides on the grant's own role edge, and the operation's shared reason
rides on the operation's node. Anything built on the graph — introspection, the
introspection UI, a reviewer reading it — then sees what a caller would be told.

Both travel beside their condition and are runtime-only, exactly as the conditions
themselves are: an interchange row still carries no callables and no prose.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestAGrantsReason      — a role condition's reason rides on that grant's edge
TestTheSharedReason    — the operation's condition carries its reason on the node
TestNothingDeclared    — no condition declared, no reason in the graph
TestRuntimeOnly        — neither reason is exported in the interchange form
"""

from __future__ import annotations

from typing import Any, cast

from aoa.action_machine.graph.edges.role_graph_edge import RoleGraphEdge
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole, ManagerRole


def _is_sales_agent(user: Any) -> bool:
    """One grant's condition."""
    return user.user_id == "sales"


def _is_region_head(user: Any) -> bool:
    """Another grant's condition, for the same role."""
    return user.user_id == "head"


def _shop_is_closed(user: Any, params: Any) -> bool:
    """The operation's shared condition."""
    return False


@meta(description="reasons: a grant that declares why it refuses", domain=SystemDomain)
@check_roles(grant(ManagerRole, when=_is_sales_agent, reason="ONLY_SALES_AGENTS"))
class WhenReasonAction(BaseAction["WhenReasonAction.Params", "WhenReasonAction.Result"]):
    """An operation whose role condition explains itself."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: one role, two conditions, two reasons", domain=SystemDomain)
@check_roles(
    grant(ManagerRole, when=_is_sales_agent, reason="ONLY_SALES_AGENTS"),
    grant(ManagerRole, when=_is_region_head, reason="ONLY_REGION_HEADS"),
)
class TwoReasonsAction(BaseAction["TwoReasonsAction.Params", "TwoReasonsAction.Result"]):
    """An operation with two ways in for one role, each explaining itself."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: a shared condition that declares why it refuses", domain=SystemDomain)
@check_roles(AdminRole, guard=_shop_is_closed, guard_reason="SHOP_CLOSED")
class GuardReasonAction(BaseAction["GuardReasonAction.Params", "GuardReasonAction.Result"]):
    """An operation whose shared condition explains itself."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: no condition to explain", domain=SystemDomain)
@check_roles(AdminRole)
class NoConditionAction(BaseAction["NoConditionAction.Params", "NoConditionAction.Result"]):
    """An operation that declares a role and no condition at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


class TestAGrantsReason:
    def test_the_edge_carries_the_condition_and_its_reason(self) -> None:
        edges = RoleGraphEdge.get_role_edges(WhenReasonAction)

        assert len(edges) == 1
        assert edges[0].properties["when"] is _is_sales_agent
        assert edges[0].properties["when_reason"] == "ONLY_SALES_AGENTS"

    def test_the_operation_node_carries_the_same_edge(self) -> None:
        node = ActionGraphNode(WhenReasonAction)

        assert node.roles[0].properties["when_reason"] == "ONLY_SALES_AGENTS"

    def test_two_conditions_for_one_role_keep_their_own_reasons(self) -> None:
        edges = RoleGraphEdge.get_role_edges(TwoReasonsAction)

        assert [edge.properties["when_reason"] for edge in edges] == [
            "ONLY_SALES_AGENTS",
            "ONLY_REGION_HEADS",
        ]
        assert [edge.properties["when"] for edge in edges] == [_is_sales_agent, _is_region_head]

    def test_the_reason_belongs_to_the_grant_not_to_the_role(self) -> None:
        """The same role twice, two edges, one reason each — not one reason per role."""
        edges = RoleGraphEdge.get_role_edges(TwoReasonsAction)

        assert {edge.target_node_id for edge in edges} == {edges[0].target_node_id}
        assert edges[0].properties["when_reason"] != edges[1].properties["when_reason"]


class TestTheSharedReason:
    def test_the_node_carries_the_condition_and_its_reason(self) -> None:
        node = ActionGraphNode(GuardReasonAction)

        assert node.properties["guard"] is _shop_is_closed
        assert node.properties["guard_reason"] == "SHOP_CLOSED"

    def test_the_declaration_hands_the_reason_over(self) -> None:
        assert CheckRolesIntentResolver.resolve_guard_reason(GuardReasonAction) == "SHOP_CLOSED"


class TestNothingDeclared:
    def test_an_operation_with_no_condition_carries_none(self) -> None:
        """No condition, so nothing explains itself — and no key is missing either."""
        node = ActionGraphNode(NoConditionAction)

        assert node.properties["guard"] is None
        assert node.properties["guard_reason"] is None
        assert node.roles[0].properties["when"] is None
        assert node.roles[0].properties["when_reason"] is None

    def test_the_declaration_hands_over_nothing(self) -> None:
        assert CheckRolesIntentResolver.resolve_guard_reason(NoConditionAction) is None


class TestRuntimeOnly:
    def test_the_edge_export_carries_no_reason(self) -> None:
        edge = RoleGraphEdge.get_role_edges(WhenReasonAction)[0]

        exported = cast("dict[str, Any]", edge.to_dict(source_id="some.Action"))

        assert exported["properties"] == {}
        assert "ONLY_SALES_AGENTS" not in str(exported)

    def test_the_node_export_carries_no_reason(self) -> None:
        exported = ActionGraphNode(GuardReasonAction).to_dict()

        assert exported["properties"] == {"description": "reasons: a shared condition that declares why it refuses"}
        assert "SHOP_CLOSED" not in str(exported)
