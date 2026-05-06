# src/action_machine/model/described_schema_validation.py
"""
Described-fields validation — enforce non-empty ``Field(description=...)`` on policy schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

:class:`~action_machine.model.base_params.BaseParams`,
:class:`~action_machine.model.base_result.BaseResult`, and
:class:`~action_machine.domain.entity.BaseEntity` subclasses participate in exported
schemas and interchange; every declared field must carry a usable description.

Callers invoke :func:`validate_described_schema` per type or
:func:`validate_described_schemas_for_action` for an action host.
"""

from __future__ import annotations

from pydantic import BaseModel


def _field_names_missing_description(model_cls: type[BaseModel]) -> list[str]:
    """Return field names with missing or empty ``Field(description=...)``."""
    missing: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        description = field_info.description
        if not description or not description.strip():
            missing.append(field_name)
    return missing


def _requires_field_descriptions(model_cls: type) -> bool:
    """True for concrete policy bases (params / result / entity stacks)."""
    # pylint: disable=import-outside-toplevel,cyclic-import
    from action_machine.domain.entity import BaseEntity
    from action_machine.model.base_params import BaseParams
    from action_machine.model.base_result import BaseResult

    return (
        issubclass(model_cls, BaseParams)
        or issubclass(model_cls, BaseResult)
        or issubclass(model_cls, BaseEntity)
    )


def validate_described_schema(model_cls: type | None) -> None:
    """
    Validate one schema class against described-fields contract.

    No-op when ``model_cls`` is ``None``, not a strict ``BaseModel`` subclass,
    not a Params/Result/Entity participant, or declares no ``model_fields``.

    Raises:
        TypeError: Any declared field lacks a non-empty ``description``.
    """
    if model_cls is None:
        return
    if not isinstance(model_cls, type):
        return
    if not issubclass(model_cls, BaseModel):
        return
    if not _requires_field_descriptions(model_cls):
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
    """Resolve ``BaseAction[P, R]`` and validate ``P`` and ``R`` descriptions."""
    # pylint: disable=import-outside-toplevel
    from action_machine.intents.action_schema.action_schema_intent_resolver import (
        ActionSchemaIntentResolver,
    )

    p_type = ActionSchemaIntentResolver.resolve_params_type(action_cls)
    r_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
    validate_described_schema(p_type)
    validate_described_schema(r_type)
