# packages/aoa-action-machine/tests/action_machine/intents/access_decide/test_access_decide_context.py
"""
Context reaches an object check the way it reaches every other declared behaviour.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The context is not free: a declared behaviour sees it only after asking, with the same
``@context_requires("user.user_id", …)`` the aspects use, and then only the keys it named —
a :class:`ContextView` refuses everything else. An object check is no exception, in either
direction:

- **without** the declaration there is no sixth parameter at all, and the step hands over the
  four things it always hands over; a declaration that grows one anyway is refused;
- **with** the declaration the parameter is required, the check receives a view restricted to
  its keys, and the graph carries those keys as ``RequiredContext`` companions, exactly as
  the aspect nodes carry theirs.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheViewArrives        — a declaration that asked for context receives it, on both paths
TestOnlyTheDeclaredKeys   — everything it did not name is refused
TestInTheGraph            — the keys are companions of the declaration's own node
TestWithoutTheDeclaration — no sixth parameter, and asking for one is refused
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import ContextAccessError
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain

_SEEN: dict[str, Any] = {}
"""What the probes below saw, so a test can read it after the call."""


@meta(description="context: a check that declares what it needs", domain=SystemDomain)
@check_roles(GuestRole)
class ContextAwareAction(BaseAction["ContextAwareAction.Params", "ContextAwareAction.Result"]):
    """An object check that asks for the caller's identifier."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow a caller whose identifier is known")
    @context_requires("user.user_id")
    async def context_aware_access_decide(
        self,
        params: ContextAwareAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        ctx: ContextView,
    ) -> Verdict:
        """Remember what arrived, and prove that only the declared key is reachable."""
        _SEEN["view"] = ctx
        _SEEN["user_id"] = ctx.get("user.user_id")
        try:
            ctx.get("request.trace_id")
        except ContextAccessError as exc:
            _SEEN["undeclared"] = type(exc).__name__
        return Allowed()

    @summary_aspect("Answer")
    async def context_aware_summary(
        self,
        params: ContextAwareAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ContextAwareAction.Result:
        """Produce the operation's result."""
        return ContextAwareAction.Result()


@meta(description="context: a check that declares nothing", domain=SystemDomain)
@check_roles(GuestRole)
class PlainCheckAction(BaseAction["PlainCheckAction.Params", "PlainCheckAction.Result"]):
    """An object check with the five parameters of the contract and nothing else."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow every caller")
    async def plain_check_access_decide(
        self,
        params: PlainCheckAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Record that the step handed over exactly what it always hands over."""
        _SEEN["plain_ran"] = True
        return Allowed()

    @summary_aspect("Answer")
    async def plain_check_summary(
        self,
        params: PlainCheckAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> PlainCheckAction.Result:
        """Produce the operation's result."""
        return PlainCheckAction.Result()


@pytest.fixture(autouse=True)
def _forget() -> Any:
    """Forget what a previous test saw."""
    _SEEN.clear()
    yield
    _SEEN.clear()


@pytest.fixture
def machine() -> ActionProductMachine:
    """A machine without a cache."""
    return ActionProductMachine(cache_coordinator=None)


def _caller() -> Context:
    """A caller whose identifier the declared key resolves to."""
    return Context(user=UserInfo(user_id="u-1", roles=(GuestRole,)))


class TestTheViewArrives:
    async def test_the_question_path_hands_over_a_restricted_view(self, machine: ActionProductMachine) -> None:
        await machine.check_access_decide(_caller(), ContextAwareAction, ContextAwareAction.Params())

        assert isinstance(_SEEN["view"], ContextView)
        assert _SEEN["user_id"] == "u-1"

    async def test_the_execution_path_hands_over_the_same_view(self, machine: ActionProductMachine) -> None:
        await machine.run(_caller(), ContextAwareAction(), ContextAwareAction.Params())

        assert isinstance(_SEEN["view"], ContextView)
        assert _SEEN["user_id"] == "u-1"

    async def test_the_key_resolves_from_the_running_call(self, machine: ActionProductMachine) -> None:
        await machine.run(_caller(), ContextAwareAction(), ContextAwareAction.Params())

        assert _SEEN["view"].get("user.user_id") == "u-1"


class TestOnlyTheDeclaredKeys:
    async def test_a_key_it_did_not_name_is_refused(self, machine: ActionProductMachine) -> None:
        """The view is a guard, not a wrapper: declaring one key does not open the context."""
        await machine.run(_caller(), ContextAwareAction(), ContextAwareAction.Params())

        assert _SEEN["undeclared"] == "ContextAccessError"


class TestInTheGraph:
    def test_the_node_carries_the_declared_keys(self) -> None:
        node = ActionGraphNode(ContextAwareAction).get_access_decide_graph_node()

        assert node is not None
        assert node.get_required_context_keys() == frozenset({"user.user_id"})

    def test_the_key_is_a_companion_node_of_its_own(self) -> None:
        node = ActionGraphNode(ContextAwareAction).get_access_decide_graph_node()

        assert node is not None
        companions = node.get_companion_nodes()

        assert [companion.node_type for companion in companions] == ["RequiredContext"]
        assert companions[0].properties["key"] == "user.user_id"

    def test_the_edge_is_materialized_on_the_declaration(self) -> None:
        node = ActionGraphNode(ContextAwareAction).get_access_decide_graph_node()

        assert node is not None
        (edge,) = node.get_all_edges()

        assert edge.properties["key"] == "user.user_id"
        assert edge.target_node is node.get_companion_nodes()[0]

    def test_a_declaration_that_asked_for_nothing_has_no_companions(self) -> None:
        node = ActionGraphNode(PlainCheckAction).get_access_decide_graph_node()

        assert node is not None
        assert node.get_required_context_keys() == frozenset()
        assert node.get_companion_nodes() == []


class TestWithoutTheDeclaration:
    async def test_a_check_that_declares_nothing_is_called_with_the_steps_own_four(
        self, machine: ActionProductMachine
    ) -> None:
        """A sixth argument would have raised; the call goes through with four."""
        await machine.run(_caller(), PlainCheckAction(), PlainCheckAction.Params())

        assert _SEEN["plain_ran"] is True

    def test_asking_for_a_sixth_parameter_without_declaring_it_is_refused(self) -> None:
        with pytest.raises(TypeError, match="must declare its parameters as"):

            @meta(description="context: a sixth parameter nobody declared", domain=SystemDomain)
            @check_roles(GuestRole)
            class UnaskedContextAction(BaseAction["UnaskedContextAction.Params", "UnaskedContextAction.Result"]):
                """An operation whose check takes a context it never asked for."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @access_decide("Answer")
                async def unasked_context_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                    ctx: ContextView,
                ) -> Verdict:
                    return Allowed()

    def test_declaring_context_without_the_parameter_is_refused(self) -> None:
        with pytest.raises(TypeError, match="must declare its parameters as"):

            @meta(description="context: declared but not taken", domain=SystemDomain)
            @check_roles(GuestRole)
            class UnusedContextAction(BaseAction["UnusedContextAction.Params", "UnusedContextAction.Result"]):
                """An operation that asks for context and never takes it."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @access_decide("Answer")
                @context_requires("user.user_id")
                async def unused_context_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                ) -> Verdict:
                    return Allowed()


class TestTheContextParameterItself:
    """``ctx`` is variable in the sense that it exists only when asked for — never in what it is."""

    def test_annotating_it_as_any_is_refused_at_assembly(self) -> None:
        @meta(description="context: ctx as Any", domain=SystemDomain)
        @check_roles(GuestRole)
        class LooseContextAction(BaseAction["LooseContextAction.Params", "LooseContextAction.Result"]):
            """An operation whose check takes the context without saying what it is."""

            class Params(BaseParams):
                """No inputs."""

            class Result(BaseResult):
                """No outputs."""

            @access_decide("Answer")
            @context_requires("user.user_id")
            async def loose_context_access_decide(
                self,
                params: BaseParams,
                box: ToolsBox,
                connections: dict[str, BaseResource],
                ctx: Any,
            ) -> Verdict:
                return Allowed()

        with pytest.raises(TypeError, match="annotates 'ctx' as Any"):
            ActionGraphNode(LooseContextAction)

    def test_annotating_it_as_the_whole_context_is_refused(self) -> None:
        """The view is the declared keys; asking for everything is not the same thing."""

        @meta(description="context: ctx as the whole Context", domain=SystemDomain)
        @check_roles(GuestRole)
        class WholeContextAction(BaseAction["WholeContextAction.Params", "WholeContextAction.Result"]):
            """An operation whose check asks for the context whole."""

            class Params(BaseParams):
                """No inputs."""

            class Result(BaseResult):
                """No outputs."""

            @access_decide("Answer")
            @context_requires("user.user_id")
            async def whole_context_access_decide(
                self,
                params: BaseParams,
                box: ToolsBox,
                connections: dict[str, BaseResource],
                ctx: Context,
            ) -> Verdict:
                return Allowed()

        with pytest.raises(TypeError, match="annotates 'ctx' as Context"):
            ActionGraphNode(WholeContextAction)

    def test_the_parameter_must_come_last(self) -> None:
        with pytest.raises(TypeError, match=r"got \(self, params, box, ctx, connections\)"):

            @meta(description="context: ctx in the middle", domain=SystemDomain)
            @check_roles(GuestRole)
            class MiddleContextAction(BaseAction["MiddleContextAction.Params", "MiddleContextAction.Result"]):
                """An operation whose check takes the context too early."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @access_decide("Answer")
                @context_requires("user.user_id")
                async def middle_context_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    ctx: ContextView,
                    connections: dict[str, BaseResource],
                ) -> Verdict:
                    return Allowed()

    def test_the_parameter_keeps_its_name(self) -> None:
        with pytest.raises(TypeError, match=r"got \(self, params, box, connections, context_view\)"):

            @meta(description="context: sixth parameter renamed", domain=SystemDomain)
            @check_roles(GuestRole)
            class RenamedContextAction(BaseAction["RenamedContextAction.Params", "RenamedContextAction.Result"]):
                """An operation whose check renames the parameter it was given."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @access_decide("Answer")
                @context_requires("user.user_id")
                async def renamed_context_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                    context_view: ContextView,
                ) -> Verdict:
                    return Allowed()


class TestTheMistakeIsExplained:
    def test_decorators_in_the_wrong_order_say_so(self) -> None:
        """``@context_requires`` above the declaration is the mistake worth naming."""
        with pytest.raises(TypeError, match=r"put @context_requires\(\.\.\.\) under the @access_decide decorator"):

            @meta(description="context: decorators the wrong way round", domain=SystemDomain)
            @check_roles(GuestRole)
            class MisorderedAction(BaseAction["MisorderedAction.Params", "MisorderedAction.Result"]):
                """An operation whose check declares context above the declaration."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @context_requires("user.user_id")
                @access_decide("Answer")
                async def misordered_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                    ctx: ContextView,
                ) -> Verdict:
                    return Allowed()

    def test_context_declared_without_the_parameter_says_so(self) -> None:
        with pytest.raises(TypeError, match="asked for context, so it must take the trailing ctx"):

            @meta(description="context: declared but not taken", domain=SystemDomain)
            @check_roles(GuestRole)
            class NotTakenAction(BaseAction["NotTakenAction.Params", "NotTakenAction.Result"]):
                """An operation that asks for context and never takes it."""

                class Params(BaseParams):
                    """No inputs."""

                class Result(BaseResult):
                    """No outputs."""

                @access_decide("Answer")
                @context_requires("user.user_id")
                async def not_taken_access_decide(
                    self,
                    params: BaseParams,
                    box: ToolsBox,
                    connections: dict[str, BaseResource],
                ) -> Verdict:
                    return Allowed()

