# src/action_machine/metadata/builder.py
"""
Модуль: builder — класс MetadataBuilder, единственная точка входа для сборки ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MetadataBuilder — статический сборщик, который обходит класс (Action, Plugin
или любой другой), читает временные атрибуты, оставленные декораторами,
валидирует структурные инварианты и конструирует иммутабельный ``ClassMetadata``.

Это единственный публичный класс подпакета ``action_machine.metadata``.

Временные атрибуты декораторов НЕ удаляются после сборки. Классы определяются
на уровне модуля и могут быть зарегистрированы в нескольких координаторах
(в тестах, при инвалидации и повторной сборке). Удаление атрибутов после
первого ``build()`` привело бы к тому, что повторная сборка возвращала бы
пустые метаданные. ``MetadataBuilder.build()`` идемпотентен — повторные
вызовы возвращают эквивалентный результат.
"""

from __future__ import annotations

from action_machine.core.class_metadata import ClassMetadata

from .collectors import (
    collect_aspects,
    collect_checkers,
    collect_connections,
    collect_dependencies,
    collect_depends_bound,
    collect_role,
    collect_sensitive_fields,
    collect_subscriptions,
    full_class_name,
)
from .validators import validate_aspects, validate_checkers_belong_to_aspects


class MetadataBuilder:
    """
    Статический сборщик ClassMetadata из временных атрибутов класса.

    Не создаёт экземпляров — единственный публичный метод ``build()``
    является статическим. Делегирует работу модулям ``collectors``
    и ``validators``.

    Временные атрибуты декораторов остаются на классе после сборки.
    Это обеспечивает идемпотентность: повторный вызов ``build()``
    для того же класса возвращает эквивалентный ``ClassMetadata``.
    Кеширование результата — ответственность ``GateCoordinator``.
    """

    @staticmethod
    def build(klass: type) -> ClassMetadata:
        """
        Собирает ``ClassMetadata`` из временных атрибутов класса.

        Выполняет: сбор → валидация → конструирование.
        Временные атрибуты остаются на классе для обеспечения идемпотентности.

        Аргументы:
            klass: класс (Action, Plugin или любой другой), метаданные
                   которого нужно собрать.

        Возвращает:
            ``ClassMetadata`` — иммутабельный снимок всех метаданных.

        Исключения:
            TypeError: если ``klass`` не является классом (``type``).
            ValueError: если нарушены структурные инварианты.
        """
        if not isinstance(klass, type):
            raise TypeError(
                f"MetadataBuilder.build() ожидает класс (type), "
                f"получен {type(klass).__name__}: {klass!r}"
            )

        class_name = full_class_name(klass)

        role = collect_role(klass)
        dependencies = collect_dependencies(klass)
        connections = collect_connections(klass)
        aspects = collect_aspects(klass)
        checkers = collect_checkers(klass)
        subscriptions = collect_subscriptions(klass)
        sensitive_fields = collect_sensitive_fields(klass)
        depends_bound = collect_depends_bound(klass)

        validate_aspects(klass, aspects)
        validate_checkers_belong_to_aspects(klass, checkers, aspects)

        return ClassMetadata(
            class_ref=klass,
            class_name=class_name,
            role=role,
            dependencies=tuple(dependencies),
            connections=tuple(connections),
            aspects=tuple(aspects),
            checkers=tuple(checkers),
            subscriptions=tuple(subscriptions),
            sensitive_fields=tuple(sensitive_fields),
            depends_bound=depends_bound,
        )