# src/action_machine/metadata/builder.py
"""
Модуль: builder — класс MetadataBuilder, единственная точка входа для сборки ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MetadataBuilder — статический сборщик, который обходит класс (Action, Plugin,
ResourceManager, Entity или любой другой), читает временные атрибуты,
оставленные декораторами, валидирует структурные инварианты и гейт-хосты,
собирает описания полей из pydantic model_fields, и конструирует
иммутабельный ``ClassMetadata``.

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ВЫПОЛНЕНИЯ В build()
═══════════════════════════════════════════════════════════════════════════════

    1. Сбор данных коллекторами (collectors.py):
       - описание и домен (@meta), роли, зависимости, соединения,
         аспекты, чекеры, обработчики ошибок, компенсаторы,
         подписки, чувствительные поля, bound-тип, описания полей
         Params и Result.
       - описание и домен (@entity), простые поля сущности, связи
         между сущностями, поля Lifecycle.

    2. Валидация обязательности @meta (validators.validate_meta_required):
       - ActionMetaGateHost + аспекты → @meta обязателен.
       - ResourceMetaGateHost → @meta обязателен.

    3. Валидация гейт-хостов (validators.validate_gate_hosts).
    4. Валидация структуры аспектов (validators.validate_aspects).
    5. Валидация привязки чекеров (validators.validate_checkers_belong_to_aspects).
    6. Валидация обработчиков ошибок (validators.validate_error_handlers).
    7. Валидация компенсаторов (validators.validate_compensators).
    8. Валидация подписок плагинов (validators.validate_subscriptions).
    9. Валидация описаний полей (validators.validate_described_fields).
   10. Конструирование ClassMetadata (frozen dataclass).

Для Entity (класс с _entity_info) коллекторы Action возвращают пустые
значения (нет _meta_info, нет _new_aspect_meta и т.д.), валидаторы
Action пропускают класс (нет ActionMetaGateHost). Entity-коллекторы
заполняют entity_info, entity_fields, entity_relations, entity_lifecycles.

═══════════════════════════════════════════════════════════════════════════════
ИДЕМПОТЕНТНОСТЬ
═══════════════════════════════════════════════════════════════════════════════

Временные атрибуты декораторов НЕ удаляются после сборки. Классы определяются
на уровне модуля и могут быть зарегистрированы в нескольких координаторах.
``MetadataBuilder.build()`` идемпотентен — повторные вызовы возвращают
эквивалентный результат.

Кеширование результата — ответственность ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.metadata import MetadataBuilder

    # Action:
    metadata = MetadataBuilder.build(CreateOrderAction)
    metadata.meta.description          # → "Создание нового заказа"
    metadata.aspects[0].context_keys   # → frozenset({"user.user_id"})

    # Entity:
    metadata = MetadataBuilder.build(OrderEntity)
    metadata.entity_info.description   # → "Заказ клиента"
    metadata.entity_fields[0].field_name  # → "id"
    metadata.entity_lifecycles[0].state_count  # → 5
"""

from __future__ import annotations

from action_machine.core.class_metadata import ClassMetadata

from .collectors import (
    collect_aspects,
    collect_checkers,
    collect_compensators,
    collect_connections,
    collect_dependencies,
    collect_depends_bound,
    collect_entity_fields,
    collect_entity_info,
    collect_entity_lifecycles,
    collect_entity_relations,
    collect_error_handlers,
    collect_meta,
    collect_params_fields,
    collect_result_fields,
    collect_role,
    collect_sensitive_fields,
    collect_subscriptions,
    full_class_name,
)
from .validators import (
    validate_aspects,
    validate_checkers_belong_to_aspects,
    validate_compensators,
    validate_described_fields,
    validate_error_handlers,
    validate_gate_hosts,
    validate_meta_required,
    validate_subscriptions,
)


class MetadataBuilder:
    """
    Статический сборщик ClassMetadata из временных атрибутов класса
    и pydantic model_fields.

    Не создаёт экземпляров — единственный публичный метод ``build()``
    является статическим.

    Обрабатывает все типы классов единообразно:
    - Action, Plugin, ResourceManager — через @meta, @check_roles,
      @depends, @regular_aspect, @summary_aspect, @on_error,
      @compensate, @on, @sensitive, @context_requires.
    - Entity — через @entity, model_fields (простые поля, связи,
      Lifecycle).

    Для Entity коллекторы Action возвращают пустые значения (None,
    пустые списки), валидаторы Action пропускают класс. Entity-коллекторы
    заполняют entity-специфичные поля ClassMetadata.
    """

    @staticmethod
    def build(klass: type) -> ClassMetadata:
        """
        Собирает ``ClassMetadata`` из временных атрибутов класса
        и pydantic model_fields.

        Аргументы:
            klass: класс (Action, Plugin, ResourceManager, Entity
                   или любой другой).

        Возвращает:
            ``ClassMetadata`` — иммутабельный снимок всех метаданных.

        Исключения:
            TypeError:
                - ``klass`` не является классом.
                - Нарушены гейт-хост инварианты.
            ValueError:
                - Нарушены структурные инварианты.
        """
        if not isinstance(klass, type):
            raise TypeError(
                f"MetadataBuilder.build() ожидает класс (type), "
                f"получен {type(klass).__name__}: {klass!r}"
            )

        class_name = full_class_name(klass)

        # ── Сбор данных: Action / Plugin / ResourceManager ─────────────
        meta = collect_meta(klass)
        role = collect_role(klass)
        dependencies = collect_dependencies(klass)
        connections = collect_connections(klass)
        aspects = collect_aspects(klass)
        checkers = collect_checkers(klass)
        error_handlers = collect_error_handlers(klass)
        compensators = collect_compensators(klass)
        subscriptions = collect_subscriptions(klass)
        sensitive_fields = collect_sensitive_fields(klass)
        depends_bound = collect_depends_bound(klass)
        params_fields = collect_params_fields(klass)
        result_fields = collect_result_fields(klass)

        # ── Сбор данных: Entity (@entity) ──────────────────────────────
        entity_info = collect_entity_info(klass)
        entity_fields = collect_entity_fields(klass) if entity_info else []
        entity_relations = collect_entity_relations(klass) if entity_info else []
        entity_lifecycles = collect_entity_lifecycles(klass) if entity_info else []

        # ── Валидация: Action / Plugin / ResourceManager ───────────────
        validate_meta_required(klass, meta, aspects)
        validate_gate_hosts(
            klass, aspects, checkers, subscriptions,
            error_handlers, compensators,
        )
        validate_aspects(klass, aspects)
        validate_checkers_belong_to_aspects(klass, checkers, aspects)
        validate_error_handlers(klass, error_handlers)
        validate_compensators(klass, compensators, aspects)
        validate_subscriptions(klass, subscriptions)
        validate_described_fields(klass, params_fields, result_fields)

        # ── Конструирование ────────────────────────────────────────────
        return ClassMetadata(
            class_ref=klass,
            class_name=class_name,
            meta=meta,
            role=role,
            dependencies=tuple(dependencies),
            connections=tuple(connections),
            aspects=tuple(aspects),
            checkers=tuple(checkers),
            error_handlers=tuple(error_handlers),
            compensators=tuple(compensators),
            subscriptions=tuple(subscriptions),
            sensitive_fields=tuple(sensitive_fields),
            depends_bound=depends_bound,
            params_fields=tuple(params_fields),
            result_fields=tuple(result_fields),
            entity_info=entity_info,
            entity_fields=tuple(entity_fields),
            entity_relations=tuple(entity_relations),
            entity_lifecycles=tuple(entity_lifecycles),
        )
