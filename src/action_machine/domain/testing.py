# src/action_machine/domain/testing.py
"""
Утилиты для создания сущностей.

═══════════════════════════════════════════════════════════════════════════════
make() — фабрика сущностей с автогенерацией дефолтов.
═══════════════════════════════════════════════════════════════════════════════

Создаёт сущность с автогенерацией дефолтов по типам полей.
Используется для быстрого создания экземпляров в тестах, примерах,
прототипировании и разработке.

Пример:
    order = make(OrderEntity, amount=100.0)
    # id сгенерируется как str, status="new" и т.д.
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


def make(entity_cls: type[T], **overrides: Any) -> T:
    """
    Создаёт тестовую сущность с автогенерацией дефолтов.

    Аргументы:
        entity_cls: класс сущности.
        **overrides: поля для переопределения.

    Возвращает:
        Экземпляр сущности.
    """
    from .lifecycle import Lifecycle  # Import here to avoid circular

    defaults = {}
    for name, field in entity_cls.model_fields.items():
        if name not in overrides:
            if field.annotation == str:
                defaults[name] = f"test_{name}"
            elif field.annotation == int:
                defaults[name] = 1
            elif field.annotation == float:
                defaults[name] = 1.0
            elif field.annotation == Lifecycle:
                # Try to get lifecycle from class method
                if hasattr(entity_cls, f'get_{name}'):
                    try:
                        defaults[name] = getattr(entity_cls, f'get_{name}')()
                    except:
                        pass
            # Add more types as needed

    data = {**defaults, **overrides}
    return entity_cls(**data)
