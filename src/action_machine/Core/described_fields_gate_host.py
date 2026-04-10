# src/action_machine/core/described_fields_gate_host.py
"""
Модуль: DescribedFieldsGateHost — marker mixin, обозначающий
обязательность описания полей через pydantic Field(description="...").

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

DescribedFieldsGateHost — миксин-маркер, который обозначает, что все поля
класса (pydantic-модели) обязаны иметь непустое описание через
``Field(description="...")``. Наследуется BaseParams и BaseResult.

MetadataBuilder при сборке метаданных проверяет: если класс наследует
DescribedFieldsGateHost и содержит pydantic-поля — каждое поле обязано
иметь непустой description. Если хотя бы одно поле без описания —
TypeError с указанием класса и поля.

Проверка выполняется только для классов с собственными полями. Базовые
классы BaseParams и BaseResult без полей не проверяются. Пустые классы
(MockParams, MockResult в тестах) тоже не проверяются — у них нет полей.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseParams(BaseSchema, DescribedFieldsGateHost):
        model_config = ConfigDict(frozen=True, extra="forbid")

    class BaseResult(BaseSchema, DescribedFieldsGateHost):
        model_config = ConfigDict(frozen=True, extra="forbid")

    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя")    ← OK
        amount: float = Field(description="Сумма заказа")       ← OK

    class BadParams(BaseParams):
        user_id: str                                             ← нет Field()
        amount: float = Field()                                  ← нет description

    # MetadataBuilder.build(Action с BadParams) → TypeError:
    # "Поле 'user_id' в BadParams не имеет описания.
    #  Используйте Field(description=\"...\")."

BaseParams и BaseResult наследуют BaseSchema [2], которая предоставляет
dict-подобный доступ к полям и dot-path навигацию через resolve().

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. МАРКЕР БЕЗ ЛОГИКИ. Миксин не содержит полей, methodов или логики.
   Его единственная функция — служить проверочным маркером для
   issubclass() в валидаторах MetadataBuilder.

2. ОБЯЗАТЕЛЬНОСТЬ. Наличие гейт-хоста в MRO класса означает, что
   каждое поле обязано иметь описание. Это безусловный инвариант.

3. ЕДИНООБРАЗИЕ. Следует тому же паттерну, что и все остальные
   гейт-миксины системы (RoleGateHost, ActionMetaGateHost,
   AspectGateHost и др.).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_params import BaseParams

    # Корректно — все поля имеют описание:
    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя")
        amount: float = Field(description="Сумма заказа", gt=0)

    # Ошибка — поле без описания:
    class BadParams(BaseParams):
        user_id: str  # → TypeError при сборке метаданных
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.core.base_action import BaseAction
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class DescribedFieldsGateHost:
    """
    Marker mixin, обозначающий обязательность описания полей
    через pydantic Field(description="...").

    Наследуется BaseParams и BaseResult. Class, наследующий
    DescribedFieldsGateHost и содержащий pydantic-поля, обязан
    иметь непустое description для каждого поля. MetadataBuilder
    проверяет это при сборке runtime metadata.

    Миксин не содержит логики, полей или methodов.
    """

    pass


def _extract_generic_params_result(cls: type) -> tuple[type | None, type | None]:
    from action_machine.core.base_action import BaseAction

    for klass in cls.__mro__:
        for base in getattr(klass, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is BaseAction:
                args = get_args(base)
                if len(args) >= 2:
                    p_type = args[0] if isinstance(args[0], type) else None
                    r_type = args[1] if isinstance(args[1], type) else None
                    return p_type, r_type
    return None, None


def _validate_pydantic_model_descriptions(model_cls: type) -> list[str]:
    if not isinstance(model_cls, type) or not issubclass(model_cls, BaseModel):
        return []

    missing: list[str] = []
    for field_name, field_info in model_cls.model_fields.items():
        description = field_info.description
        if not description or not description.strip():
            missing.append(field_name)
    return missing


def validate_described_fields(
    cls: type,
    params_fields: list[Any],
    result_fields: list[Any],
) -> None:
    """Инварианты DescribedFieldsGateHost для Params/Result (вызов из builder)."""
    p_type, r_type = _extract_generic_params_result(cls)

    if (
        p_type is not None
        and issubclass(p_type, DescribedFieldsGateHost)
        and params_fields
    ):
        missing = _validate_pydantic_model_descriptions(p_type)
        if missing:
            fields_str = ", ".join(f"'{f}'" for f in missing)
            raise TypeError(
                f"Поля {fields_str} в {p_type.__name__} не имеют описания. "
                f'Используйте Field(description="...") для каждого поля.'
            )

    if (
        r_type is not None
        and issubclass(r_type, DescribedFieldsGateHost)
        and result_fields
    ):
        missing = _validate_pydantic_model_descriptions(r_type)
        if missing:
            fields_str = ", ".join(f"'{f}'" for f in missing)
            raise TypeError(
                f"Поля {fields_str} в {r_type.__name__} не имеют описания. "
                f'Используйте Field(description="...") для каждого поля.'
            )


class DescribedFieldsGateHostInspector(BaseGateHostInspector):
    """Inspector that captures Params/Result field descriptions for actions."""

    _target_mixin: type = BaseAction

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
        params_fields: tuple[FieldDescription, ...]
        result_fields: tuple[FieldDescription, ...]

        def to_facet_payload(self) -> FacetPayload:
            def _to_row(fd: DescribedFieldsGateHostInspector.Snapshot.FieldDescription) -> tuple[Any, ...]:
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
                node_name=DescribedFieldsGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=DescribedFieldsGateHostInspector._make_meta(
                    params_fields=tuple(_to_row(f) for f in self.params_fields),
                    result_fields=tuple(_to_row(f) for f in self.result_fields),
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
        return cls._collect_subclasses(cls._target_mixin)

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
        result: list[DescribedFieldsGateHostInspector.Snapshot.FieldDescription] = []
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
    def _collect_fields_for_action(
        cls, target_cls: type,
    ) -> tuple[tuple[Snapshot.FieldDescription, ...], tuple[Snapshot.FieldDescription, ...]]:
        p_type, r_type = _extract_generic_params_result(target_cls)
        return cls._collect_pydantic_fields(p_type), cls._collect_pydantic_fields(r_type)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        params_fields, result_fields = cls._collect_fields_for_action(target_cls)
        if not params_fields and not result_fields:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> Snapshot | None:
        params_fields, result_fields = cls._collect_fields_for_action(target_cls)
        if not params_fields and not result_fields:
            return None
        return cls.Snapshot(
            class_ref=target_cls,
            params_fields=params_fields,
            result_fields=result_fields,
        )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "described_fields"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        snap = cls.facet_snapshot_for_class(target_cls)
        if snap is None:
            return FacetPayload(
                node_type="described_fields",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                node_meta=(),
                edges=(),
            )
        return snap.to_facet_payload()
