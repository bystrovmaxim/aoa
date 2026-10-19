# packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_types.py
"""
Tests for what an aspect declaration is typed as — at declaration, and at assembly.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The annotations are the contract: they say what the pipeline hands over and what the
declaration reads back. These tests pin both halves of that — an annotation is required
where the method is written, and the type it names is checked when the capability is
assembled, because ``params`` is typed with the operation's own ``Params``, a name that
does not exist while the class body runs.

Every negative fixture lives inside the ``pytest.raises`` block that asserts its refusal,
for two reasons: the declaration is what the test is about, and a declaration written
outside such a block would read to the corpus scan as a mistake left in the tree rather
than as the test of a rule.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheAnnotationsAreRequired     — a bare parameter or return is refused, per decorator
TestTheTypesAreCheckedAtAssembly  — the parameter types, the compensator's two states, the error
TestTheReturnIsCheckedAtAssembly  — the operation's Result, a state fragment, nothing at all
TestTheHintsAreResolvable         — forward references, the operation's own names, a local class
TestTheRefusalItself              — which moment it says, and what it can be caught as
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.exceptions import AspectSignatureError, SignatureContractError
from aoa.action_machine.graph.nodes.compensator_graph_node import CompensatorGraphNode
from aoa.action_machine.graph.nodes.error_handler_graph_node import ErrorHandlerGraphNode
from aoa.action_machine.graph.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from aoa.action_machine.graph.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState, ParamsStub, ResultStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain


class OtherResult(BaseResult):
    """A result type that belongs to some other operation."""


async def _target_aspect(self: Any, params: Any, state: Any, box: Any, connections: Any) -> dict[str, Any]:
    """A target regular aspect, for the compensator's required reference."""
    return {}


def _declared(node_class: type[Any], suffix: str, marker: str) -> Any:
    """Return the own-class method whose name ends with ``suffix`` and carries ``marker``."""
    return next(
        value
        for name, value in vars(node_class).items()
        if callable(value) and name.endswith(suffix) and hasattr(value, marker)
    )


def _summary_node(action_cls: type[Any]) -> SummaryAspectGraphNode:
    """Build the summary interchange node, which is where a summary is checked at assembly."""
    return SummaryAspectGraphNode(_declared(action_cls, "_summary", "_new_aspect_meta"), action_cls)


def _regular_node(action_cls: type[Any]) -> RegularAspectGraphNode:
    """Build the regular-aspect interchange node."""
    return RegularAspectGraphNode(_declared(action_cls, "_aspect", "_new_aspect_meta"), action_cls)


def _handler_node(action_cls: type[Any]) -> ErrorHandlerGraphNode:
    """Build the on-error interchange node."""
    return ErrorHandlerGraphNode(_declared(action_cls, "_on_error", "_on_error_meta"), action_cls)


def _compensator_node(action_cls: type[Any]) -> CompensatorGraphNode:
    """Build the compensator interchange node."""
    return CompensatorGraphNode(_declared(action_cls, "_compensate", "_compensate_meta"), action_cls)


class TestTheAnnotationsAreRequired:
    """A bare parameter or return is refused while the method is declared."""

    def test_a_bare_parameter_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="must annotate every parameter"):

            @summary_aspect("S")
            async def bare_summary(self, params: ParamsStub, state, box, connections) -> ResultStub:
                return ResultStub()

    def test_a_bare_return_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="must annotate what it returns"):

            @summary_aspect("S")
            async def silent_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections):
                return ResultStub()

    def test_self_may_stay_bare(self) -> None:
        @summary_aspect("S")
        async def acceptable_summary(self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections) -> ResultStub:
            return ResultStub()

        assert acceptable_summary.__name__ == "acceptable_summary"

    def test_each_decorator_asks_for_the_same_discipline(self) -> None:
        with pytest.raises(AspectSignatureError, match="must annotate every parameter"):

            @regular_aspect("R")
            async def bare_aspect(self, params, state, box, connections) -> dict[str, Any]:
                return {}

        with pytest.raises(AspectSignatureError, match="must annotate every parameter"):

            @on_error(ValueError, description="E")
            async def bare_on_error(self, params, state, box, connections, error) -> ResultStub:
                return ResultStub()

        with pytest.raises(AspectSignatureError, match="must annotate every parameter"):

            @compensate(_target_aspect, "C")
            async def bare_compensate(
                self,
                params,
                state_before,
                state_after,
                box,
                connections,
                error,
            ) -> None:
                return None


class TestTheTypesAreCheckedAtAssembly:
    """The parameter types are refused when the capability is assembled."""

    def test_a_wrong_box_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="annotates 'box' as str"):

            @meta(description="types: a box that is not a tool box", domain=SystemDomain)
            @check_roles(GuestRole)
            class WrongBoxAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def wrong_box_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: str,
                    connections: Connections,
                ) -> ResultStub:
                    return ResultStub()

            _summary_node(WrongBoxAction)

    def test_a_bare_connections_mapping_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="must be Connections"):

            @meta(description="types: connections that are not resources", domain=SystemDomain)
            @check_roles(GuestRole)
            class LooseConnectionsAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def loose_connections_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: dict[str, Any],
                ) -> ResultStub:
                    return ResultStub()

            _summary_node(LooseConnectionsAction)

    def test_a_wrong_state_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="annotates 'state' as dict"):

            @meta(description="types: a state that is not a state", domain=SystemDomain)
            @check_roles(GuestRole)
            class WrongStateAction(BaseAction[ParamsStub, ResultStub]):
                @regular_aspect("R")
                async def wrong_state_aspect(
                    self,
                    params: ParamsStub,
                    state: dict,
                    box: ToolsBox,
                    connections: Connections,
                ) -> dict[str, Any]:
                    return {}

            _regular_node(WrongStateAction)

    def test_a_bare_error_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="annotates 'error' as dict"):

            @meta(description="types: an error that is not an exception", domain=SystemDomain)
            @check_roles(GuestRole)
            class WrongErrorAction(BaseAction[ParamsStub, ResultStub]):
                @on_error(ValueError, description="E")
                async def wrong_error_on_error(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                    error: dict,
                ) -> ResultStub:
                    return ResultStub()

            _handler_node(WrongErrorAction)

    def test_the_union_state_of_a_compensator_is_accepted(self) -> None:
        @meta(description="types: a compensator with the union state", domain=SystemDomain)
        @check_roles(GuestRole)
        class UnionStateAction(BaseAction[ParamsStub, ResultStub]):
            @regular_aspect("R")
            async def union_state_aspect(
                self,
                params: ParamsStub,
                state: BaseState,
                box: ToolsBox,
                connections: Connections,
            ) -> dict[str, Any]:
                return {}

            @compensate(union_state_aspect, "C")
            async def union_state_compensate(
                self,
                params: ParamsStub,
                state_before: BaseState,
                state_after: BaseState | None,
                box: ToolsBox,
                connections: Connections,
                error: Exception,
            ) -> None:
                return None

        assert _compensator_node(UnionStateAction).label == "union_state_compensate"


class TestTheReturnIsCheckedAtAssembly:
    """The return is checked against what the pipeline does with it."""

    def test_a_summary_annotated_any_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="a summary answers with the operation's Result"):

            @meta(description="types: a summary that promises anything", domain=SystemDomain)
            @check_roles(GuestRole)
            class AnyReturnAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def any_return_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                ) -> Any:
                    return ResultStub()

            _summary_node(AnyReturnAction)

    def test_a_summary_with_another_operations_result_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="OtherResult"):

            @meta(description="types: a summary that promises a foreign result", domain=SystemDomain)
            @check_roles(GuestRole)
            class ForeignResultAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def foreign_result_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                ) -> OtherResult:
                    return OtherResult()

            _summary_node(ForeignResultAction)

    def test_a_summary_may_promise_the_base_result(self) -> None:
        @meta(description="types: a summary that promises the base result", domain=SystemDomain)
        @check_roles(GuestRole)
        class BaseReturnAction(BaseAction[ParamsStub, ResultStub]):
            @summary_aspect("S")
            async def base_return_summary(
                self,
                params: ParamsStub,
                state: BaseState,
                box: ToolsBox,
                connections: Connections,
            ) -> BaseResult:
                return ResultStub()

        assert _summary_node(BaseReturnAction).label == "base_return_summary"

    def test_a_regular_aspect_returning_something_other_than_a_mapping_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="a regular aspect answers with the state fragment"):

            @meta(description="types: a regular aspect that promises a string", domain=SystemDomain)
            @check_roles(GuestRole)
            class StringReturnAction(BaseAction[ParamsStub, ResultStub]):
                @regular_aspect("R")
                async def string_return_aspect(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                ) -> str:
                    return "state"

            _regular_node(StringReturnAction)

    def test_a_compensator_returning_something_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="a compensator answers with nothing"):

            @meta(description="types: a compensator that promises a mapping", domain=SystemDomain)
            @check_roles(GuestRole)
            class MappingCompensatorAction(BaseAction[ParamsStub, ResultStub]):
                @regular_aspect("R")
                async def mapping_compensator_aspect(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                ) -> dict[str, Any]:
                    return {}

                @compensate(mapping_compensator_aspect, "C")
                async def mapping_compensate(
                    self,
                    params: ParamsStub,
                    state_before: BaseState,
                    state_after: BaseState | None,
                    box: ToolsBox,
                    connections: Connections,
                    error: Exception,
                ) -> dict[str, Any]:
                    return {}

            _compensator_node(MappingCompensatorAction)


class TestTheHintsAreResolvable:
    """The operation's own names resolve, whether the operation is module-level or local."""

    def test_a_forward_reference_to_the_operations_own_result_is_accepted(self) -> None:
        @meta(description="types: the operation's own names", domain=SystemDomain)
        @check_roles(GuestRole)
        class LocalAction(BaseAction["LocalAction.Params", "LocalAction.Result"]):
            class Params(BaseParams):
                pass

            class Result(BaseResult):
                pass

            @summary_aspect("S")
            async def local_summary(
                self,
                params: LocalAction.Params,
                state: BaseState,
                box: ToolsBox,
                connections: Connections,
            ) -> LocalAction.Result:
                return LocalAction.Result()

        assert _summary_node(LocalAction).label == "local_summary"

    def test_a_name_that_never_resolves_is_refused(self) -> None:
        with pytest.raises(AspectSignatureError, match="cannot be resolved"):

            @meta(description="types: a name that does not exist", domain=SystemDomain)
            @check_roles(GuestRole)
            class UnresolvableAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def unresolvable_summary(
                    self,
                    params: NeverDefinedAnywhere,  # noqa: F821
                    state: BaseState,
                    box: ToolsBox,
                    connections: Connections,
                ) -> ResultStub:
                    return ResultStub()

            _summary_node(UnresolvableAction)


class TestTheRefusalItself:
    """Which moment the message names, and what the error can be caught as."""

    def test_an_assembly_refusal_says_so(self) -> None:
        with pytest.raises(AspectSignatureError) as caught:

            @meta(description="types: the moment the refusal happened", domain=SystemDomain)
            @check_roles(GuestRole)
            class MomentAction(BaseAction[ParamsStub, ResultStub]):
                @summary_aspect("S")
                async def moment_summary(
                    self,
                    params: ParamsStub,
                    state: BaseState,
                    box: str,
                    connections: Connections,
                ) -> ResultStub:
                    return ResultStub()

            _summary_node(MomentAction)

        assert "assembled" in str(caught.value)

    def test_a_declaration_refusal_does_not_claim_assembly(self) -> None:
        with pytest.raises(AspectSignatureError) as caught:

            @summary_aspect("S")
            async def early_summary(self, params, state, box, connections) -> ResultStub:
                return ResultStub()

        assert "class body was executing" in str(caught.value)

    def test_the_error_is_the_shape_error_and_a_type_error(self) -> None:
        assert issubclass(AspectSignatureError, SignatureContractError)
        assert issubclass(AspectSignatureError, TypeError)
