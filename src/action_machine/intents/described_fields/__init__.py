# src/action_machine/intents/described_fields/__init__.py
"""Described-fields intent (marker); inspector: ``action_machine.graph.inspectors.described_fields_intent_inspector``."""

from action_machine.intents.described_fields.marker import (
    DescribedFieldsIntent,
    validate_described_schema,
    validate_described_schemas_for_action,
)

__all__ = [
    "DescribedFieldsIntent",
    "validate_described_schema",
    "validate_described_schemas_for_action",
]
