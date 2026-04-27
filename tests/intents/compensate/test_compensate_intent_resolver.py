from action_machine.intents.compensate.compensate_intent_resolver import (
    CompensateIntentResolver,
)
from tests.scenarios.domain_model.compensate_actions import CompensatedOrderAction


def test_resolve_compensators_returns_own_compensators() -> None:
    assert CompensateIntentResolver.resolve_compensators(CompensatedOrderAction) == [
        CompensatedOrderAction.rollback_charge_compensate,
        CompensatedOrderAction.rollback_reserve_compensate,
    ]
