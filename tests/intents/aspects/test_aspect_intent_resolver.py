from tests.scenarios.domain_model.child_action import ChildAction

from action_machine.intents.aspects.regular_aspect_intent_resolver import (
    RegularAspectIntentResolver,
)
from action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)


def test_resolve_regular_aspects_returns_own_regular_aspects() -> None:
    assert RegularAspectIntentResolver.resolve_regular_aspects(ChildAction) == [
        ChildAction.process_aspect,
    ]


def test_resolve_summary_aspects_returns_own_summary_aspects() -> None:
    assert SummaryAspectIntentResolver.resolve_summary_aspects(ChildAction) == [
        ChildAction.build_result_summary,
    ]
