import pytest

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from tests.action_machine.scenarios.domain_model.ping_action import PingAction


class NoActionSchema:
    pass


def test_resolve_params_type_returns_base_params_subclass() -> None:
    assert ActionSchemaIntentResolver.resolve_params_type(PingAction) is PingAction.Params


def test_resolve_result_type_returns_base_result_subclass() -> None:
    assert ActionSchemaIntentResolver.resolve_result_type(PingAction) is PingAction.Result


def test_resolve_schema_types_raise_without_action_generic() -> None:
    with pytest.raises(ValueError, match="Failed to resolve params type"):
        ActionSchemaIntentResolver.resolve_params_type(NoActionSchema)
    with pytest.raises(ValueError, match="Failed to resolve result type"):
        ActionSchemaIntentResolver.resolve_result_type(NoActionSchema)
