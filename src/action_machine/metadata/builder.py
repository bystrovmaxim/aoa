# src/action_machine/metadata/builder.py
"""
Модуль: builder — класс MetadataBuilder, единственная точка входа для сборки ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MetadataBuilder — статический сборщик, который обходит класс (Action, Plugin,
ResourceManager или любой другой), читает временные атрибуты, оставленные
декораторами, валидирует структурные инварианты и гейт-хосты, собирает
описания полей Params и Result из pydantic model_fields, и конструирует
иммутабельный ``ClassMetadata``.

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ВЫПОЛНЕНИЯ В build()
═══════════════════════════════════════════════════════════════════════════════

    1. Сбор данных коллекторами (collectors.py):
       - описание и домен (@meta), роли, зависимости, соединения,
         аспекты, чекеры, обработчики ошибок, подписки, чувствительные
         поля, bound-тип, описания полей Params и Result.

    2. Валидация обязательности @meta (validators.validate_meta_required):
       - ActionMetaGateHost + аспекты → @meta обязателен.
       - ResourceMetaGateHost → @meta обязателен.

    3. Валидация гейт-хостов (validators.validate_gate_hosts):
       - Аспекты → AspectGateHost.
       - Чекеры → CheckerGateHost.
       - Подписки → OnGateHost.
       - Обработчики ошибок → OnErrorGateHost.

    4. Валидация структуры аспектов (validators.validate_aspects).

    5. Валидация привязки чекеров (validators.validate_checkers_belong_to_aspects).

    6. Валидация обработчиков ошибок (validators.validate_error_handlers):
       - Нижестоящий обработчик не перекрывается вышестоящим.

    7. Валидация описаний полей (validators.validate_described_fields):
       - Params с DescribedFieldsGateHost → каждое поле обязано иметь description.
       - Result с DescribedFieldsGateHost → каждое поле обязано иметь description.

    8. Конструирование ClassMetadata (frozen dataclass).

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

    metadata = MetadataBuilder.build(CreateOrderAction)
    # metadata.meta.description → "Создание нового заказа"
    # metadata.error_handlers[0].exception_types → (ValueError,)
    # metadata.params_fields[0].description → "ID пользователя"
"""

from __future__ import annotations

from action_machine.core.class_metadata import ClassMetadata

from .collectors import (
    collect_aspects,
    collect_checkers,
    collect_connections,
    collect_dependencies,
    collect_depends_bound,
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
    validate_described_fields,
    validate_error_handlers,
    validate_gate_hosts,
    validate_meta_required,
)


class MetadataBuilder:
    """
    Статический сборщик ClassMetadata из временных атрибутов класса
    и pydantic model_fields.

    Не создаёт экземпляров — единственный публичный метод ``build()``
    является статическим.

    Порядок валидации:
        1. validate_meta_required — обязательность @meta.
        2. validate_gate_hosts — гейт-хосты для декораторов уровня метода.
        3. validate_aspects — структурные инварианты аспектов.
        4. validate_checkers_belong_to_aspects — привязка чекеров.
        5. validate_error_handlers — перекрытие типов обработчиков ошибок.
        6. validate_described_fields — обязательность описаний полей Params/Result.
    """

    @staticmethod
    def build(klass: type) -> ClassMetadata:
        """
        Собирает ``ClassMetadata`` из временных атрибутов класса
        и pydantic model_fields.

        Аргументы:
            klass: класс (Action, Plugin, ResourceManager или любой другой).

        Возвращает:
            ``ClassMetadata`` — иммутабельный снимок всех метаданных.

        Исключения:
            TypeError:
                - ``klass`` не является классом.
                - Класс наследует ActionMetaGateHost с аспектами без @meta.
                - Класс наследует ResourceMetaGateHost без @meta.
                - Класс содержит аспекты без AspectGateHost.
                - Класс содержит чекеры без CheckerGateHost.
                - Класс содержит подписки без OnGateHost.
                - Класс содержит обработчики ошибок без OnErrorGateHost.
                - Поле Params или Result не имеет description.
                - Нижестоящий обработчик ошибок перекрывается вышестоящим.
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
        meta = collect_meta(klass)
        role = collect_role(klass)
        dependencies = collect_dependencies(klass)
        connections = collect_connections(klass)
        aspects = collect_aspects(klass)
        checkers = collect_checkers(klass)
        error_handlers = collect_error_handlers(klass)
        subscriptions = collect_subscriptions(klass)
        sensitive_fields = collect_sensitive_fields(klass)
        depends_bound = collect_depends_bound(klass)
        params_fields = collect_params_fields(klass)
        result_fields = collect_result_fields(klass)

        # ── Валидация обязательности @meta (ПЕРВАЯ) ────────────────────
        validate_meta_required(klass, meta, aspects)

        # ── Валидация гейт-хостов ──────────────────────────────────────
        validate_gate_hosts(klass, aspects, checkers, subscriptions, error_handlers)

        # ── Валидация структуры аспектов ───────────────────────────────
        validate_aspects(klass, aspects)

        # ── Валидация привязки чекеров ─────────────────────────────────
        validate_checkers_belong_to_aspects(klass, checkers, aspects)

        # ── Валидация обработчиков ошибок (перекрытие типов) ───────────
        validate_error_handlers(klass, error_handlers)

        # ── Валидация описаний полей Params и Result ───────────────────
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
            subscriptions=tuple(subscriptions),
            sensitive_fields=tuple(sensitive_fields),
            depends_bound=depends_bound,
            params_fields=tuple(params_fields),
            result_fields=tuple(result_fields),
        )
