# packages/aoa-action-machine/tests/action_machine/intents/aspects/test_duplicate_summary_aspect.py
"""
Tests for the refusal a second summary aspect earns — and for the two it must not.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An operation answers once. Two ``@summary_aspect`` methods mean two exit points, and the
machine cannot say which one decided, so the declaration is refused while the capability
is assembled.

What the refusal must not be is the failure it used to be: a graph error naming an edge
whose target node does not exist — a message about a node the developer never wrote, in
place of the sentence that names both methods. The tests below assert the message and the
absence of that phrase, because the absence is the whole point of the change.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTwoSummaries           — refused, naming both, before any node is built
TestWhatTheRefusalIsNot    — never a missing graph node, never a `None` or a silent pick
TestTheNeighboursOfTheRule — one summary passes, none is a different refusal entirely
"""

from __future__ import annotations

import pytest

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.exceptions import DuplicateSummaryAspectError, MissingSummaryAspectError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.aspects.summary_aspect_intent_resolver import SummaryAspectIntentResolver
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseState, ParamsStub, ResultStub
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain


@exclude_graph_model
@meta(description="duplicate: two exit points", domain=SystemDomain)
@check_roles(GuestRole)
class TwoSummariesAction(BaseAction[ParamsStub, ResultStub]):
    """An operation that declares two summary aspects."""

    @summary_aspect("First exit point")
    async def first_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ResultStub:
        """Assemble the result, first way."""
        return ResultStub()

    @summary_aspect("Second exit point")
    async def second_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ResultStub:
        """Assemble the result, second way."""
        return ResultStub()


@exclude_graph_model
@meta(description="duplicate: one exit point", domain=SystemDomain)
@check_roles(GuestRole)
class OneSummaryAction(BaseAction[ParamsStub, ResultStub]):
    """An operation with exactly one summary aspect."""

    @summary_aspect("The only exit point")
    async def only_summary(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ResultStub:
        """Assemble the result."""
        return ResultStub()


@exclude_graph_model
@meta(description="duplicate: no exit point at all", domain=SystemDomain)
@check_roles(GuestRole)
class NoSummaryAction(BaseAction[ParamsStub, ResultStub]):
    """An operation with a regular aspect and no summary."""

    @regular_aspect("Do something on the way")
    async def step_aspect(
        self,
        params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, object]:
        """Return an empty state fragment."""
        return {}


class TestTwoSummaries:
    """A second summary is refused, and the refusal names both."""

    def test_the_resolver_refuses_two_summaries(self) -> None:
        with pytest.raises(DuplicateSummaryAspectError) as caught:
            SummaryAspectIntentResolver.resolve_summary_aspects(TwoSummariesAction)

        message = str(caught.value)
        assert "first_summary" in message
        assert "second_summary" in message
        assert "TwoSummariesAction" in message

    def test_the_message_says_the_operation_answers_once(self) -> None:
        with pytest.raises(DuplicateSummaryAspectError, match="answers once"):
            SummaryAspectIntentResolver.resolve_summary_aspects(TwoSummariesAction)

    def test_the_refusal_happens_at_assembly_not_at_declaration(self) -> None:
        """The class exists — declaring is not the mistake; assembling is where it surfaces."""
        assert TwoSummariesAction.first_summary is not None

        with pytest.raises(DuplicateSummaryAspectError):
            ActionGraphNode(TwoSummariesAction)

    def test_the_refusal_is_catchable_as_a_type_error(self) -> None:
        assert issubclass(DuplicateSummaryAspectError, TypeError)
        with pytest.raises(TypeError):
            SummaryAspectIntentResolver.resolve_summary_aspects(TwoSummariesAction)


class TestWhatTheRefusalIsNot:
    """Never a missing graph node, and never a silent choice among two."""

    def test_the_message_does_not_name_a_missing_target_node(self) -> None:
        with pytest.raises(DuplicateSummaryAspectError) as caught:
            SummaryAspectIntentResolver.resolve_summary_aspects(TwoSummariesAction)

        assert "missing target_node_id" not in str(caught.value)
        assert "InvalidGraphError" not in str(caught.value)

    def test_the_graph_does_not_report_a_missing_node_either(self) -> None:
        with pytest.raises(DuplicateSummaryAspectError) as caught:
            ActionGraphNode(TwoSummariesAction)

        assert "missing target_node_id" not in str(caught.value)

    def test_the_resolver_does_not_pick_one_silently(self) -> None:
        with pytest.raises(DuplicateSummaryAspectError):
            SummaryAspectIntentResolver.resolve_summary_aspects(TwoSummariesAction)


class TestTheNeighboursOfTheRule:
    """The two declarations either side of the rule keep their own answers."""

    def test_one_summary_is_returned_unchanged(self) -> None:
        assert SummaryAspectIntentResolver.resolve_summary_aspects(OneSummaryAction) == [
            OneSummaryAction.only_summary,
        ]

    def test_no_summary_is_an_empty_list_not_a_refusal(self) -> None:
        assert SummaryAspectIntentResolver.resolve_summary_aspects(NoSummaryAction) == []

    def test_no_summary_still_raises_the_missing_summary_error(self) -> None:
        node = ActionGraphNode(NoSummaryAction)
        with pytest.raises(MissingSummaryAspectError):
            node.get_summary_aspect_graph_node()
