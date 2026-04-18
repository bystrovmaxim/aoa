# src/action_machine/intents/described_fields/marker.py
"""
Described-fields marker mixin and validation helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module defines the ``DescribedFieldsIntent`` marker and lightweight
validators that enforce ``Field(description="...")`` contracts on schema
classes used by actions.

The graph inspector lives in
``action_machine.intents.described_fields.described_fields_intent_inspector``,
colocated with this marker, to avoid import cycles between intents and graph layers.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Validation is opt-in via ``DescribedFieldsIntent`` inheritance.
- Only ``BaseModel`` subclasses with declared fields are validated.
- Validation functions are read-only and never mutate input classes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action schemas (Params/Result)
               |
               v
    DescribedFieldsIntent marker
               |
               +--> validate_described_schema(model_cls)
               |        |
               |        +--> _field_names_missing_description(...)
               |
               +--> validate_described_schemas_for_action(action_cls)
                        |
                        +--> extract_action_params_result_types(action_cls)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class Params(BaseParams, DescribedFieldsIntent):
        name: str = Field(description="Name")

    validate_described_schema(Params)

    # Edge case: field without description -> TypeError.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``TypeError`` when any validated field has missing/empty description.
- Non-marker classes and non-``BaseModel`` types are skipped by design.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Enforce schema-field description contracts for marked models.
CONTRACT: Validate marker-bearing schemas and action-linked Params/Result.
INVARIANTS: Validation-only logic; no cross-layer graph imports.
FLOW: model/action type input -> description checks -> fail-fast TypeError.
FAILURES: Missing field descriptions trigger validation exceptions.
EXTENSION POINTS: Add extra schema-level validators in this marker module.
AI-CORE-END
"""

from __future__ import annotations

from pydantic import BaseModel

from action_machine.runtime.binding.extract_action_params_result_types import (
    extract_action_params_result_types,
)


class DescribedFieldsIntent:
    """
    Marker mixin requiring described Pydantic fields.

    AI-CORE-BEGIN
    ROLE: Opt-in marker for described-field validation policy.
    CONTRACT: Classes inheriting this marker must provide field descriptions.
    INVARIANTS: Enforcement is performed by dedicated validation helpers.
    AI-CORE-END
    """

    pass


def _field_names_missing_description(model_cls: type[BaseModel]) -> list[str]:
    """Return field names with missing or empty ``Field(description=...)``."""
    missing: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        description = field_info.description
        if not description or not description.strip():
            missing.append(field_name)
    return missing


def validate_described_schema(model_cls: type | None) -> None:
    """
    Validate one schema class against described-fields contract.

    No-op when ``model_cls`` is ``None``, is not a ``DescribedFieldsIntent`` subtype,
    is not a ``BaseModel`` subclass, or declares no fields (empty schema shells).

    Raises:
        TypeError: Any declared field lacks a non-empty ``description``.
    """
    if model_cls is None:
        return
    if not isinstance(model_cls, type):
        return
    if not issubclass(model_cls, DescribedFieldsIntent):
        return
    if not issubclass(model_cls, BaseModel):
        return
    if not model_cls.model_fields:
        return
    missing = _field_names_missing_description(model_cls)
    if missing:
        fields_str = ", ".join(f"'{f}'" for f in missing)
        raise TypeError(
            f"Fields {fields_str} in {model_cls.__name__} do not have descriptions. "
            f'Use Field(description="...") for each field.'
        )


def validate_described_schemas_for_action(action_cls: type) -> None:
    """
    Resolve ``BaseAction[P, R]`` on ``action_cls`` and validate ``P`` and ``R``.

    Each resolved type is passed to :func:`validate_described_schema`.
    """
    p_type, r_type = extract_action_params_result_types(action_cls)
    validate_described_schema(p_type)
    validate_described_schema(r_type)
