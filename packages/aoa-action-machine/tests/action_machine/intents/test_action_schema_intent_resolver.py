import sys

import pytest

from aoa.action_machine.exceptions import ActionResultDeclarationError
from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver

from ...support.domain_model.ping_action import PingAction


class NoActionSchema:
    pass


def test_resolve_params_type_returns_base_params_subclass() -> None:
    assert ActionSchemaIntentResolver.resolve_params_type(PingAction) is PingAction.Params


def test_resolve_result_type_returns_base_result_subclass() -> None:
    assert ActionSchemaIntentResolver.resolve_result_type(PingAction) is PingAction.Result


def test_resolve_schema_types_raise_without_action_generic() -> None:
    with pytest.raises(ActionResultDeclarationError, match="Failed to resolve params type"):
        ActionSchemaIntentResolver.resolve_params_type(NoActionSchema)
    with pytest.raises(ActionResultDeclarationError, match="Failed to resolve result type"):
        ActionSchemaIntentResolver.resolve_result_type(NoActionSchema)


def test_string_generic_arguments_resolve_on_python_3_12_3(monkeypatch: pytest.MonkeyPatch) -> None:
    """``BaseAction["X.Params", "X.Result"]`` resolves where ``ForwardRef._evaluate`` has no ``type_params`` (3.12.0–3.12.3)."""
    import typing

    from aoa.action_machine.intents.action_schema import action_schema_intent_resolver as resolver

    from ..adapters.json_schema_adapter_fixtures import AdapterTestAction

    if sys.version_info >= (3, 12, 4):
        # On a newer interpreter the real ``_evaluate`` takes ``type_params``; simulate the older signature.
        current = typing.ForwardRef._evaluate

        def evaluate_before_3_12_4(self, globalns, localns, recursive_guard):  # the signature 3.12.0–3.12.3 had
            return current(self, globalns, localns, (), recursive_guard=recursive_guard)

        monkeypatch.setattr(typing.ForwardRef, "_evaluate", evaluate_before_3_12_4)
    # On 3.12.0–3.12.3 the interpreter already has that older signature: use it as it is.
    monkeypatch.setattr(resolver, "_EVALUATE_TAKES_TYPE_PARAMS", False)
    assert ActionSchemaIntentResolver.resolve_params_type(AdapterTestAction) is AdapterTestAction.Params
    assert ActionSchemaIntentResolver.resolve_result_type(AdapterTestAction) is AdapterTestAction.Result
