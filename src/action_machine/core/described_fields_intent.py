# src/action_machine/core/described_fields_intent.py
"""
DescribedFieldsIntent и DescribedFieldsIntentInspector — намерение самодокументируемых полей.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DescribedFieldsIntent`` маркирует ``BaseParams`` / ``BaseResult`` (и любые pydantic-модели
в роли P/R действия): каждое поле с данными обязано иметь непустой
``Field(description=...)``.

``DescribedFieldsIntentInspector`` обходит подклассы ``DescribedFieldsIntent``, читает
поля каждой **модели-схемы** и эмитит узел фасета ``described_fields`` для
``GateCoordinator``. Связь «действие → свои P/R`` задаётся отдельно
:class:`ActionTypedSchemasInspector` (узлы ``action_schemas`` с рёбрами к этим узлам).

Класс ``DescribedFieldsIntent`` (миксин):
    Намерение: все pydantic-поля носителя снабжены явными описаниями; проверка через
    ``validate_described_schema`` / ``validate_described_schemas_for_action`` при сборке
    метаданных (MetadataBuilder и т.п.).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Миксин без логики; только маркер для ``issubclass`` и контракта с билдером.
- Проверка срабатывает для классов с собственными полями; пустые ``BaseParams`` /
  ``BaseResult`` и модели без полей не валидируются.
- Тексты ошибок формулируются как невыполненное **намерение описать поля**, не как
  «отсутствие разрешения».
- Ключ фасета в координаторе для схемы — ``described_fields`` (по классу модели).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя")

    → described_fields:tests…OrderParams (поля + constraints)

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]): ...

    → action_schemas:…CreateOrderAction — рёбра uses_params / uses_result
      к узлам described_fields для OrderParams и OrderResult
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.core.action_generic_params import extract_action_params_result_types
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload


class DescribedFieldsIntent:
    """
    Marker mixin, обозначающий обязательность описания полей
    через pydantic Field(description="...").

    Наследуется BaseParams и BaseResult. Class, наследующий
    DescribedFieldsIntent и содержащий pydantic-поля, обязан
    иметь непустое description для каждого поля.     Вызывайте ``validate_described_schema`` на классе модели или
    ``validate_described_schemas_for_action`` на классе действия при сборке метаданных.

    Миксин не содержит логики, полей или methodов.
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


class DescribedFieldsIntentInspector(BaseIntentInspector):
    """Inspector: pydantic field docs for each class that carries ``DescribedFieldsIntent``."""

    _target_intent: type = DescribedFieldsIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        @dataclass(frozen=True)
        class FieldDescription:
            field_name: str
            field_type: str
            description: str
            examples: tuple[Any, ...] | None
            constraints: dict[str, Any]
            required: bool
            default: Any

        class_ref: type
        fields: tuple[FieldDescription, ...]

        def to_facet_payload(self) -> FacetPayload:
            def _to_row(fd: DescribedFieldsIntentInspector.Snapshot.FieldDescription) -> tuple[Any, ...]:
                return (
                    fd.field_name,
                    fd.field_type,
                    fd.description,
                    fd.examples,
                    tuple(fd.constraints.items()),
                    fd.required,
                    fd.default,
                )

            return FacetPayload(
                node_type="described_fields",
                node_name=DescribedFieldsIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=DescribedFieldsIntentInspector._make_meta(
                    schema_fields=tuple(_to_row(f) for f in self.fields),
                ),
                edges=(),
            )

    _CONSTRAINT_ATTRS: tuple[str, ...] = (
        "gt", "ge", "lt", "le",
        "min_length", "max_length",
        "pattern",
        "multiple_of",
        "strict",
    )

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def _extract_constraints(cls, field_info: FieldInfo) -> dict[str, Any]:
        constraints: dict[str, Any] = {}
        for attr in cls._CONSTRAINT_ATTRS:
            value = getattr(field_info, attr, None)
            if value is not None:
                constraints[attr] = value
        for meta_item in field_info.metadata or []:
            for attr in cls._CONSTRAINT_ATTRS:
                value = getattr(meta_item, attr, None)
                if value is not None and attr not in constraints:
                    constraints[attr] = value
        return constraints

    @classmethod
    def _collect_pydantic_fields(
        cls, model_cls: type | None,
    ) -> tuple[Snapshot.FieldDescription, ...]:
        if model_cls is None or not isinstance(model_cls, type) or not issubclass(model_cls, BaseModel):
            return ()
        model_fields = model_cls.model_fields
        if not model_fields:
            return ()
        result: list[DescribedFieldsIntentInspector.Snapshot.FieldDescription] = []
        for field_name, field_info in model_fields.items():
            annotation = field_info.annotation
            field_type_str = str(annotation) if annotation is not None else "Any"
            if annotation is not None and hasattr(annotation, "__name__"):
                field_type_str = annotation.__name__
            is_required = field_info.is_required()
            result.append(
                cls.Snapshot.FieldDescription(
                    field_name=field_name,
                    field_type=field_type_str,
                    description=field_info.description or "",
                    examples=tuple(field_info.examples) if field_info.examples is not None else None,
                    constraints=cls._extract_constraints(field_info),
                    required=is_required,
                    default=field_info.default if not is_required else PydanticUndefined,
                ),
            )
        return tuple(result)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        fields = cls._collect_pydantic_fields(target_cls)
        if not fields:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> Snapshot | None:
        fields = cls._collect_pydantic_fields(target_cls)
        if not fields:
            return None
        return cls.Snapshot(class_ref=target_cls, fields=fields)

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "described_fields"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_payload()
