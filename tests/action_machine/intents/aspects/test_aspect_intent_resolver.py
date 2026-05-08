import pytest
from tests.action_machine.scenarios.domain_model.child_action import ChildAction

from aoa.action_machine.intents.aspects.regular_aspect_intent_resolver import (
    RegularAspectIntentResolver,
)
from aoa.action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)


def test_resolve_regular_aspects_returns_own_regular_aspects() -> None:
    assert RegularAspectIntentResolver.resolve_regular_aspects(ChildAction) == [
        ChildAction.process_aspect,
    ]


def test_resolve_description_returns_decorator_string() -> None:
    assert RegularAspectIntentResolver.resolve_description(ChildAction.process_aspect) == "Process value"


def test_resolve_description_raises_when_not_regular_aspect() -> None:
    async def naked(self, params, state, box, connections):  # type: ignore[no-untyped-def]
        return {}

    with pytest.raises(ValueError, match="no usable @regular_aspect"):
        RegularAspectIntentResolver.resolve_description(naked)


def test_resolve_summary_aspects_returns_own_summary_aspects() -> None:
    assert SummaryAspectIntentResolver.resolve_summary_aspects(ChildAction) == [
        ChildAction.build_result_summary,
    ]


def test_resolve_summary_description_returns_decorator_string() -> None:
    assert (
        SummaryAspectIntentResolver.resolve_description(ChildAction.build_result_summary)
        == "Build result"
    )


def test_resolve_summary_description_raises_when_not_summary_aspect() -> None:
    async def naked(self, params, state, box, connections):  # type: ignore[no-untyped-def]
        return None

    with pytest.raises(ValueError, match="no usable @summary_aspect"):
        SummaryAspectIntentResolver.resolve_description(naked)
