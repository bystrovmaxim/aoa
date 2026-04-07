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
         аспекты (с context_keys из @context_requires), чекеры,
         обработчики ошибок (с context_keys из @context_requires),
         компенсаторы (с context_keys из @context_requires),
         подписки, чувствительные поля, bound-тип, описания полей
         Params и Result.

    2. Валидация обязательности @meta (validators.validate_meta_required):
       - ActionMetaGateHost + аспекты → @meta обязателен.
       - ResourceMetaGateHost → @meta обязателен.

    3. Валидация гейт-хостов (validators.validate_gate_hosts):
       - Аспекты → AspectGateHost.
       - Чекеры → CheckerGateHost.
       - Подписки → OnGateHost.
       - Обработчики ошибок → OnErrorGateHost.
       - Контекстные зависимости (аспекты, обработчики, компенсаторы)
         → ContextRequiresGateHost.

    4. Валидация структуры аспектов (validators.validate_aspects).

    5. Валидация привязки чекеров (validators.validate_checkers_belong_to_aspects).

    6. Валидация обработчиков ошибок (validators.validate_error_handlers):
       - Нижестоящий обработчик не перекрывается вышестоящим.

    7. Валидация компенсаторов (validators.validate_compensators):
       - Каждый компенсатор привязан к существующему аспекту.
       - Целевой аспект имеет тип "regular" (не "summary").
       - Для одного аспекта — не более одного компенсатора.
       Компенсаторы валидируются ПОСЛЕ аспектов и чекеров, но ПЕРЕД
       подписками — потому что зависят от уже собранных aspects.

    8. Валидация подписок плагинов (validators.validate_subscriptions):
       - event_class из @on совместим с аннотацией параметра event.

    9. Валидация описаний полей (validators.validate_described_fields):
       - Params с DescribedFieldsGateHost → каждое поле обязано иметь description.
       - Result с DescribedFieldsGateHost → каждое поле обязано иметь description.

   10. Конструирование ClassMetadata (frozen dataclass).

═══════════════════════════════════════════════════════════════════════════════
КОНТЕКСТНЫЕ ЗАВИСИМОСТИ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @context_requires записывает _required_context_keys в метод.
Коллекторы collect_aspects, collect_error_handlers и collect_compensators
читают этот атрибут и включают в AspectMeta.context_keys,
OnErrorMeta.context_keys и CompensatorMeta.context_keys соответственно.

Валидация гейт-хоста ContextRequiresGateHost выполняется в
validate_gate_hosts: если хотя бы один аспект, обработчик или компенсатор
имеет непустые context_keys — класс обязан наследовать
ContextRequiresGateHost.

Согласованность количества параметров метода с наличием @context_requires
проверяется декораторами @regular_aspect, @summary_aspect, @on_error
и @compensate на этапе определения класса (до вызова MetadataBuilder).

═══════════════════════════════════════════════════════════════════════════════
КОМПЕНСАТОРЫ (SAGA)
═══════════════════════════════════════════════════════════════════════════════

Коллектор collect_compensators читает _compensate_meta с методов текущего
класса (vars(cls)) и создаёт CompensatorMeta. Компенсаторы НЕ наследуются
от родительских классов — каждый Action объявляет свои компенсаторы явно.

Валидатор validate_compensators проверяет:
    - Привязка к существующему аспекту (target_aspect_name).
    - Целевой аспект имеет тип "regular" (не "summary").
    - Уникальность: один аспект — один компенсатор.

Все проверки выполняются ДО обработки первого запроса (fail-fast).
Приложение не запустится при нарушении любого инварианта.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ ПОДПИСОК ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════

Функция validate_subscriptions проверяет совместимость event_class из @on
с аннотацией параметра event в сигнатуре обработчика. event_class должен
быть подклассом аннотации (или совпадать). Если аннотация — GlobalFinishEvent,
а event_class — GlobalLifecycleEvent, обработчик может получить
GlobalStartEvent без полей GlobalFinishEvent — это ошибка типизации,
обнаруживаемая при сборке.

Валидация выполняется ПОСЛЕ validate_gate_hosts (которая подтвердила
наличие OnGateHost) и ПОСЛЕ validate_compensators. Это гарантирует,
что к моменту проверки подписок все остальные инварианты уже проверены.

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
    # metadata.aspects[0].context_keys → frozenset({"user.user_id"})
    # metadata.error_handlers[0].context_keys → frozenset()
    # metadata.compensators[0].target_aspect_name → "process_payment_aspect"
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

    Порядок валидации:
        1. validate_meta_required — обязательность @meta.
        2. validate_gate_hosts — гейт-хосты для декораторов уровня метода
           (включая ContextRequiresGateHost для @context_requires
           в аспектах, обработчиках и компенсаторах).
        3. validate_aspects — структурные инварианты аспектов.
        4. validate_checkers_belong_to_aspects — привязка чекеров.
        5. validate_error_handlers — перекрытие типов обработчиков ошибок.
        6. validate_compensators — привязка, тип аспекта, уникальность.
        7. validate_subscriptions — совместимость event_class ↔ аннотация event.
        8. validate_described_fields — обязательность описаний полей Params/Result.
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
                - Класс содержит @context_requires без ContextRequiresGateHost.
                - event_class из @on несовместим с аннотацией event.
                - Поле Params или Result не имеет description.
                - Нижестоящий обработчик ошибок перекрывается вышестоящим.
            ValueError:
                - Нарушены структурные инварианты аспектов.
                - Чекер привязан к несуществующему аспекту.
                - Компенсатор привязан к несуществующему аспекту.
                - Компенсатор привязан к summary-аспекту.
                - Дублирование компенсаторов для одного аспекта.
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
        compensators = collect_compensators(klass)
        subscriptions = collect_subscriptions(klass)
        sensitive_fields = collect_sensitive_fields(klass)
        depends_bound = collect_depends_bound(klass)
        params_fields = collect_params_fields(klass)
        result_fields = collect_result_fields(klass)

        # ── Валидация обязательности @meta (ПЕРВАЯ) ────────────────────
        validate_meta_required(klass, meta, aspects)

        # ── Валидация гейт-хостов (включая ContextRequiresGateHost) ────
        # Компенсаторы передаются для проверки @context_requires:
        # если компенсатор использует @context_requires, класс обязан
        # наследовать ContextRequiresGateHost.
        validate_gate_hosts(
            klass, aspects, checkers, subscriptions,
            error_handlers, compensators,
        )

        # ── Валидация структуры аспектов ───────────────────────────────
        validate_aspects(klass, aspects)

        # ── Валидация привязки чекеров ─────────────────────────────────
        validate_checkers_belong_to_aspects(klass, checkers, aspects)

        # ── Валидация обработчиков ошибок (перекрытие типов) ───────────
        validate_error_handlers(klass, error_handlers)

        # ── Валидация компенсаторов ────────────────────────────────────
        # Выполняется ПОСЛЕ аспектов и чекеров (зависит от собранных
        # aspects), но ПЕРЕД подписками.
        validate_compensators(klass, compensators, aspects)

        # ── Валидация подписок плагинов (event_class ↔ аннотация) ──────
        validate_subscriptions(klass, subscriptions)

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
            compensators=tuple(compensators),
            subscriptions=tuple(subscriptions),
            sensitive_fields=tuple(sensitive_fields),
            depends_bound=depends_bound,
            params_fields=tuple(params_fields),
            result_fields=tuple(result_fields),
        )
