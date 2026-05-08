# tests/runtime/binding/test_action_result_runtime_validation.py
"""Resolution of declared action result types (`ActionSchemaIntentResolver`)."""

from __future__ import annotations

import pytest

from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)


def test_resolve_result_type_plain_class_raises_value_error() -> None:
    class _Plain:
        pass

    with pytest.raises(ValueError, match="Failed to resolve result type"):
        ActionSchemaIntentResolver.resolve_result_type(_Plain)
