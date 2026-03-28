# src/action_machine/metadata/builder.py
"""
Модуль: builder — класс MetadataBuilder, единственная точка входа для сборки ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MetadataBuilder — статический сборщик, который обходит класс (Action, Plugin
или любой другой), читает временные атрибуты, оставленные декораторами,
валидирует структурные инварианты и гейт-хосты, и конструирует иммутабельный
``ClassMetadata``.

Это единственный публичный класс подпакета ``action_machine.metadata``.

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ВЫПОЛНЕНИЯ В build()
═══════════════════════════════════════════════════════════════════════════════

    1. Сбор данных коллекторами (collectors.py):
       - роли, зависимости, соединения, аспекты, чекеры,
         подписки, чувствительные поля, bound-тип.

    2. Валидация гейт-хостов (validators.validate_gate_hosts):
       - Аспекты → AspectGateHost.
       - Чекеры → CheckerGateHost.
       - Подписки → OnGateHost.
       Если класс содержит декораторы, но не наследует соответствующий
       гейт-хост — TypeError. Это дополняет проверки декораторов
       уровня класса (@CheckRoles, @depends, @connection), которые
       проверяют гейты самостоятельно.

    3. Валидация структуры аспектов (validators.validate_aspects):
       - Не более одного summary.
       - Regular без summary — ошибка.
       - Summary последним.

    4. Валидация привязки чекеров (validators.validate_checkers_belong_to_aspects):
       - Чекер привязан к существующему аспекту.

    5. Конструирование ClassMetadata (frozen dataclass).

═══════════════════════════════════════════════════════════════════════════════
ИДЕМПОТЕНТНОСТЬ
═══════════════════════════════════════════════════════════════════════════════

Временные атрибуты декораторов НЕ удаляются после сборки. Классы определяются
на уровне модуля и могут быть зарегистрированы в нескольких координаторах
(в тестах, при инвалидации и повторной сборке). Удаление атрибутов после
первого ``build()`` привело бы к тому, что повторная сборка возвращала бы
пустые метаданные. ``MetadataBuilder.build()`` идемпотентен — повторные
вызовы возвращают эквивалентный результат.

Кеширование результата — ответственность ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.metadata import MetadataBuilder

    metadata = MetadataBuilder.build(CreateOrderAction)
    # metadata — иммутабельный ClassMetadata
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
from .validators import (
    validate_aspects,
    validate_checkers_belong_to_aspects,
    validate_gate_hosts,
)


class MetadataBuilder:
    """
    Статический сборщик ClassMetadata из временных атрибутов класса.

    Не создаёт экземпляров — единственный публичный метод ``build()``
    является статическим. Делегирует работу модулям ``collectors``
    и ``validators``.

    Порядок валидации:
        1. validate_gate_hosts — проверка гейт-хостов для декораторов
           уровня метода (аспекты → AspectGateHost, чекеры → CheckerGateHost,
           подписки → OnGateHost). Выполняется ПЕРВОЙ, чтобы ошибка
           отсутствия гейта не маскировалась ошибками структуры аспектов.
        2. validate_aspects — структурные инварианты аспектов.
        3. validate_checkers_belong_to_aspects — привязка чекеров к аспектам.
    """

    @staticmethod
    def build(klass: type) -> ClassMetadata:
        """
        Собирает ``ClassMetadata`` из временных атрибутов класса.

        Выполняет: сбор → валидация гейтов → валидация структуры → конструирование.

        Аргументы:
            klass: класс (Action, Plugin или любой другой), метаданные
                   которого нужно собрать.

        Возвращает:
            ``ClassMetadata`` — иммутабельный снимок всех метаданных.

        Исключения:
            TypeError:
                - ``klass`` не является классом (``type``).
                - Класс содержит аспекты, но не наследует ``AspectGateHost``.
                - Класс содержит чекеры, но не наследует ``CheckerGateHost``.
                - Класс содержит подписки, но не наследует ``OnGateHost``.
            ValueError:
                - Нарушены структурные инварианты аспектов.
                - Чекер привязан к несуществующему аспекту.
        """
        if not isinstance(klass, type):
            raise TypeError(
                f"MetadataBuilder.build() ожидает класс (type), "
                f"получен {type(klass).__name__}: {klass!r}"
            )

        class_name = full_class_name(klass)

        # ── Сбор данных ────────────────────────────────────────────────
        role = collect_role(klass)
        dependencies = collect_dependencies(klass)
        connections = collect_connections(klass)
        aspects = collect_aspects(klass)
        checkers = collect_checkers(klass)
        subscriptions = collect_subscriptions(klass)
        sensitive_fields = collect_sensitive_fields(klass)
        depends_bound = collect_depends_bound(klass)

        # ── Валидация гейт-хостов (ПЕРВАЯ) ────────────────────────────
        # Проверяет, что декораторы уровня метода применены к классам
        # с соответствующими гейт-хостами. Декораторы уровня класса
        # (@CheckRoles, @depends, @connection) проверяют гейты сами.
        validate_gate_hosts(klass, aspects, checkers, subscriptions)

        # ── Валидация структуры ────────────────────────────────────────
        validate_aspects(klass, aspects)
        validate_checkers_belong_to_aspects(klass, checkers, aspects)

        # ── Конструирование ────────────────────────────────────────────
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
