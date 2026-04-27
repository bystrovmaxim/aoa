from action_machine.intents.on_error.on_error_intent_resolver import (
    OnErrorIntentResolver,
)
from tests.scenarios.domain_model.compensate_actions import CompensateAndOnErrorAction


def test_resolve_error_handlers_returns_own_error_handlers() -> None:
    assert OnErrorIntentResolver.resolve_error_handlers(CompensateAndOnErrorAction) == [
        CompensateAndOnErrorAction.handle_finalize_on_error,
    ]
