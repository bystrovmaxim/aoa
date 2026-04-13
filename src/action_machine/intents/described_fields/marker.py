# src/action_machine/intents/described_fields/marker.py
"""
Marker mixin ``DescribedFieldsIntent`` and validation helpers (no graph imports).

Inspector lives in ``action_machine.graph.inspectors.described_fields_intent_inspector``
to avoid import cycles between ``intents`` and ``graph``.
"""

from __future__ import annotations

from pydantic import BaseModel

from action_machine.runtime.binding.action_generic_params import extract_action_params_result_types


class DescribedFieldsIntent:
    """
    Marker mixin: pydantic fields must use ``Field(description="...")``.

    See ``DescribedFieldsIntentInspector`` docstring for full design notes.
    """

    pass


def _field_names_missing_description(model_cls: type[BaseModel]) -> list[str]:
    """Return names of model fields with missing or empty ``Field(description=...)``."""
    missing: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        description = field_info.description
        if not description or not description.strip():
            missing.append(field_name)
    return missing


def validate_described_schema(model_cls: type | None) -> None:
    """
    Enforce ``DescribedFieldsIntent`` for one Pydantic model class.

    No-op when ``model_cls`` is ``None``, is not a ``DescribedFieldsIntent`` subtype,
    is not a ``BaseModel`` subclass, or declares no fields (empty schema shells).

    Raises:
        TypeError: A declared field lacks a non-empty ``description``.
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
            f"Поля {fields_str} в {model_cls.__name__} не имеют описания. "
            f'Используйте Field(description="...") для каждого поля.'
        )


def validate_described_schemas_for_action(action_cls: type) -> None:
    """
    Resolve ``BaseAction[P, R]`` on ``action_cls`` and validate ``P`` and ``R``.

    Each resolved type is passed to :func:`validate_described_schema`.
    """
    p_type, r_type = extract_action_params_result_types(action_cls)
    validate_described_schema(p_type)
    validate_described_schema(r_type)
