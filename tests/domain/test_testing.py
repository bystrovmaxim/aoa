# src/action_machine/domain/testing.py
"""
Утилиты для создания сущностей.

═══════════════════════════════════════════════════════════════════════════════

make() — фабрика сущностей с автогенерацией дефолтов.

═══════════════════════════════════════════════════════════════════════════════

Создаёт сущность с автогенерацией дефолтов по типам полей.
Используется для быстрого создания экземпляров в тестах, примерах,
прототипировании и разработке.

Для полей Lifecycle (и подклассов) генерирует экземпляр с первым
начальным состоянием из _template. Для Optional[Lifecycle] подставляет None.

Пример:
    order = make(OrderEntity, amount=100.0)
"""

from __future__ import annotations

import types
import typing
from typing import Any, TypeVar, get_args, get_origin

T = TypeVar("T")


def _is_optional(annotation: Any) -> bool:
    """Проверяет, является ли аннотация Optional (X | None)."""
    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return type(None) in get_args(annotation)
    return False


def _extract_lifecycle_default(annotation: Any) -> Any:
    """
    Пытается создать дефолтный экземпляр Lifecycle из аннотации.

    Если аннотация — подкласс Lifecycle с _template, создаёт экземпляр
    с первым начальным состоянием. Если Optional — возвращает None.
    """
    from action_machine.domain.lifecycle import Lifecycle  # pylint: disable=import-outside-toplevel

    # Optional[DraftLifecycle] → None
    if _is_optional(annotation):
        return None

    # Прямой тип: DraftLifecycle
    if isinstance(annotation, type) and issubclass(annotation, Lifecycle):
        template = annotation._get_template() if hasattr(annotation, "_get_template") else None
        if template is not None:
            initial_keys = template.get_initial_keys()
            if initial_keys:
                first_initial = sorted(initial_keys)[0]
                return annotation(first_initial)
        return None

    return None


def make(entity_cls: type[T], **overrides: Any) -> T:
    """
    Создаёт тестовую сущность с автогенерацией дефолтов.

    Генерирует значения по типам полей:
    - str → "test_{field_name}"
    - int → 1
    - float → 1.0
    - Lifecycle подкласс → экземпляр с первым начальным состоянием
    - Optional[Lifecycle] → None
    - Остальные Optional → None

    Аргументы:
        entity_cls: класс сущности.
        **overrides: поля для переопределения.

    Возвращает:
        Экземпляр сущности.
    """

    defaults: dict[str, Any] = {}

    for name, field in entity_cls.model_fields.items():
        if name in overrides:
            continue

        annotation = field.annotation

        # Проверяем Lifecycle (и подклассы)
        lc_default = _extract_lifecycle_default(annotation)
        if lc_default is not None:
            defaults[name] = lc_default
            continue

        # Проверяем Optional — для Union с None
        if _is_optional(annotation):
            defaults[name] = None
            continue

        # Базовые типы
        if annotation == str:
            defaults[name] = f"test_{name}"
        elif annotation == int:
            defaults[name] = 1
        elif annotation == float:
            defaults[name] = 1.0

    data = {**defaults, **overrides}
    return entity_cls(**data)
