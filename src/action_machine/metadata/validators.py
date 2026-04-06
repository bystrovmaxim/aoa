# src/action_machine/metadata/validators.py
"""
Модуль: validators — функции структурной валидации собранных метаданных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит функции валидации, которые проверяют структурные инварианты
собранных метаданных. Эти инварианты невозможно проверить на уровне
отдельного декоратора — они требуют знания обо всех декораторах класса
в совокупности.

Все проверки выполняются в MetadataBuilder.build() при первом обращении
к классу через GateCoordinator, ДО обработки первого запроса. Нарушение
любого инварианта — ошибка, приложение не запускается.

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

Обязательность описаний полей (validate_described_fields):
    1. Если Params наследует DescribedFieldsGateHost и имеет поля —
       каждое поле обязано иметь непустой description.
    2. Если Result наследует DescribedFieldsGateHost и имеет поля —
       каждое поле обязано иметь непустой description.

Обязательность @meta (validate_meta_required):
    3. ActionMetaGateHost + аспекты → @meta обязателен.
    4. ResourceMetaGateHost → @meta обязателен.

Гейт-хосты (validate_gate_hosts):
    5. Аспекты → AspectGateHost.
    6. Чекеры → CheckerGateHost.
    7. Подписки → OnGateHost.
    8. Обработчики ошибок → OnErrorGateHost.
    9. Контекстные зависимости → ContextRequiresGateHost.

Аспекты (validate_aspects):
    10. Не более одного summary-аспекта.
    11. Regular без summary — ошибка.
    12. Summary последним.

Чекеры (validate_checkers_belong_to_aspects):
    13. Каждый чекер привязан к существующему аспекту.

Обработчики ошибок (validate_error_handlers):
    14. Нижестоящий обработчик не перекрывается вышестоящим.

Подписки плагинов (validate_subscriptions):
    15. event_class из @on совместим с аннотацией параметра event
        в сигнатуре обработчика: event_class должен быть подклассом
        аннотации (или совпадать). Если аннотация — GlobalFinishEvent,
        а event_class — GlobalLifecycleEvent, это ошибка: обработчик
        получит GlobalStartEvent, у которого нет полей GlobalFinishEvent.
    16. aspect_name_pattern указан только для подписок на AspectEvent
        и наследники. Проверяется в SubscriptionInfo.__post_init__,
        но дублируется здесь для полноты диагностики.

Контекстные зависимости:
    17. Если метод имеет context_keys — класс обязан наследовать
        ContextRequiresGateHost.
    18. Согласованность наличия @context_requires и количества параметров
        метода проверяется декораторами @regular_aspect, @summary_aspect
        и @on_error на этапе определения класса (не здесь).
"""

from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.context.context_requires_gate_host import ContextRequiresGateHost
from action_machine.core.class_metadata import (
    AspectMeta,
    CheckerMeta,
    FieldDescriptionMeta,
    MetaInfo,
    OnErrorMeta,
)
from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.on_error.on_error_gate_host import OnErrorGateHost
from action_machine.plugins.events import BasePluginEvent
from action_machine.plugins.on_gate_host import OnGateHost
from action_machine.plugins.subscription_info import SubscriptionInfo

# ═════════════════════════════════════════════════════════════════════════════
# Валидация описаний полей Params и Result
#
# Если класс Params или Result наследует DescribedFieldsGateHost и содержит
# pydantic-поля — каждое поле обязано иметь непустой description в Field().
# Пустые классы (без собственных полей) не проверяются.
# ═════════════════════════════════════════════════════════════════════════════


def _extract_generic_params_result(cls: type) -> tuple[type | None, type | None]:
    """
    Извлекает generic-параметры P и R из BaseAction[P, R] в MRO класса.

    Аргументы:
        cls: класс действия.

    Возвращает:
        Кортеж (P, R). Если не найдены — (None, None).
    """
    from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

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
    """
    Проверяет, что все поля pydantic-модели имеют непустой description.

    Аргументы:
        model_cls: pydantic-класс для проверки.

    Возвращает:
        Список имён полей без описания. Пустой список если всё OK.
    """
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
    params_fields: list[FieldDescriptionMeta],
    result_fields: list[FieldDescriptionMeta],
) -> None:
    """
    Проверяет обязательность описаний полей Params и Result.

    Извлекает generic-параметры P и R из BaseAction[P, R]. Для каждого
    проверяет: если класс наследует DescribedFieldsGateHost и содержит
    pydantic-поля — каждое поле обязано иметь непустой description.

    Пустые классы (BaseParams, BaseResult без собственных полей,
    MockParams и т.д.) не проверяются.

    Аргументы:
        cls: класс действия для анализа.
        params_fields: собранные описания полей Params.
        result_fields: собранные описания полей Result.

    Исключения:
        TypeError: если хотя бы одно поле не имеет описания.
    """
    p_type, r_type = _extract_generic_params_result(cls)

    # Проверка Params
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

    # Проверка Result
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


# ═════════════════════════════════════════════════════════════════════════════
# Валидация обязательности @meta
# ═════════════════════════════════════════════════════════════════════════════


def validate_meta_required(
    cls: type,
    meta: MetaInfo | None,
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет обязательность декоратора @meta для классов с гейт-хостами.

    Правила:
        1. ActionMetaGateHost + аспекты → @meta обязателен.
        2. ResourceMetaGateHost → @meta обязателен.

    Аргументы:
        cls: класс, который проверяется.
        meta: собранные метаданные @meta (или None).
        aspects: собранные аспекты.

    Исключения:
        TypeError: если класс обязан иметь @meta, но декоратор не применён.
    """
    if meta is not None:
        return

    if issubclass(cls, ActionMetaGateHost) and aspects:
        raise TypeError(
            f"Action {cls.__name__} не имеет декоратора @meta. "
            f"Каждое действие обязано иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )

    if issubclass(cls, ResourceMetaGateHost):
        raise TypeError(
            f"Ресурсный менеджер {cls.__name__} не имеет декоратора @meta. "
            f"Каждый ресурсный менеджер обязан иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация гейт-хостов
# ═════════════════════════════════════════════════════════════════════════════


def _has_any_context_keys(
    aspects: list[AspectMeta],
    error_handlers: list[OnErrorMeta],
) -> bool:
    """
    Проверяет, есть ли хотя бы один аспект или обработчик ошибок
    с непустыми context_keys.

    Аргументы:
        aspects: собранные аспекты.
        error_handlers: собранные обработчики ошибок.

    Возвращает:
        True если хотя бы один метод имеет непустые context_keys.
    """
    for aspect in aspects:
        if aspect.context_keys:
            return True
    for handler in error_handlers:
        if handler.context_keys:
            return True
    return False


def validate_gate_hosts(
    cls: type,
    aspects: list[AspectMeta],
    checkers: list[CheckerMeta],
    subscriptions: list[Any],
    error_handlers: list[OnErrorMeta],
) -> None:
    """
    Проверяет, что класс наследует необходимые гейт-хосты для всех
    обнаруженных декораторов уровня метода.

    Проверки:
        - Аспекты → AspectGateHost.
        - Чекеры → CheckerGateHost.
        - Подписки → OnGateHost.
        - Обработчики ошибок → OnErrorGateHost.
        - Контекстные зависимости → ContextRequiresGateHost.

    Для подписок в диагностическом сообщении выводятся имена классов
    событий (event_class.__name__) вместо строковых event_type.

    Аргументы:
        cls: класс, который проверяется.
        aspects: собранные аспекты.
        checkers: собранные чекеры.
        subscriptions: собранные подписки (list[SubscriptionInfo]).
        error_handlers: собранные обработчики ошибок.

    Исключения:
        TypeError: если класс содержит декораторы без гейт-хоста.
    """
    if aspects and not issubclass(cls, AspectGateHost):
        aspect_names = ", ".join(a.method_name for a in aspects)
        raise TypeError(
            f"Класс {cls.__name__} содержит аспекты ({aspect_names}), "
            f"но не наследует AspectGateHost. Декораторы @regular_aspect "
            f"и @summary_aspect разрешены только на классах, наследующих "
            f"AspectGateHost. Используйте BaseAction или добавьте "
            f"AspectGateHost в цепочку наследования."
        )

    if checkers and not issubclass(cls, CheckerGateHost):
        checker_fields = ", ".join(c.field_name for c in checkers)
        raise TypeError(
            f"Класс {cls.__name__} содержит чекеры для полей ({checker_fields}), "
            f"но не наследует CheckerGateHost. Декораторы чекеров "
            f"(@result_string, @result_int и др.) разрешены "
            f"только на классах, наследующих CheckerGateHost. "
            f"Используйте BaseAction или добавьте CheckerGateHost "
            f"в цепочку наследования."
        )

    if subscriptions and not issubclass(cls, OnGateHost):
        event_classes = ", ".join(
            s.event_class.__name__ if isinstance(s, SubscriptionInfo) else str(s)
            for s in subscriptions
        )
        raise TypeError(
            f"Класс {cls.__name__} содержит подписки на события ({event_classes}), "
            f"но не наследует OnGateHost. Декоратор @on разрешён только "
            f"на классах, наследующих OnGateHost. Используйте Plugin "
            f"или добавьте OnGateHost в цепочку наследования."
        )

    if error_handlers and not issubclass(cls, OnErrorGateHost):
        handler_names = ", ".join(h.method_name for h in error_handlers)
        raise TypeError(
            f"Класс {cls.__name__} содержит обработчики ошибок ({handler_names}), "
            f"но не наследует OnErrorGateHost. Декоратор @on_error разрешён "
            f"только на классах, наследующих OnErrorGateHost. "
            f"Используйте BaseAction или добавьте OnErrorGateHost "
            f"в цепочку наследования."
        )

    if _has_any_context_keys(aspects, error_handlers) and not issubclass(cls, ContextRequiresGateHost):
        methods_with_ctx: list[str] = []
        for a in aspects:
            if a.context_keys:
                methods_with_ctx.append(a.method_name)
        for h in error_handlers:
            if h.context_keys:
                methods_with_ctx.append(h.method_name)
        methods_str = ", ".join(methods_with_ctx)
        raise TypeError(
            f"Класс {cls.__name__} содержит методы с @context_requires "
            f"({methods_str}), но не наследует ContextRequiresGateHost. "
            f"Декоратор @context_requires разрешён только на классах, "
            f"наследующих ContextRequiresGateHost. Используйте BaseAction "
            f"или добавьте ContextRequiresGateHost в цепочку наследования."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация аспектов
# ═════════════════════════════════════════════════════════════════════════════


def validate_aspects(cls: type, aspects: list[AspectMeta]) -> None:
    """
    Проверяет структурные инварианты аспектов.

    Правила:
        1. Не более одного summary-аспекта.
        2. Regular без summary — ошибка.
        3. Summary последним.

    Аргументы:
        cls: класс для сообщений об ошибках.
        aspects: собранные аспекты.

    Исключения:
        ValueError: при нарушении инвариантов.
    """
    if not aspects:
        return

    summaries = [a for a in aspects if a.aspect_type == "summary"]
    regulars = [a for a in aspects if a.aspect_type == "regular"]

    if len(summaries) > 1:
        names = ", ".join(s.method_name for s in summaries)
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(summaries)} summary-аспектов "
            f"({names}), допускается не более одного."
        )

    if regulars and not summaries:
        raise ValueError(
            f"Класс {cls.__name__} содержит {len(regulars)} regular-аспект(ов), "
            f"но не имеет summary-аспекта. Действие должно завершаться "
            f"summary-аспектом, возвращающим Result."
        )

    if summaries and aspects[-1].aspect_type != "summary":
        raise ValueError(
            f"Класс {cls.__name__}: summary-аспект '{summaries[0].method_name}' "
            f"должен быть объявлен последним методом среди аспектов. "
            f"Сейчас последний аспект — '{aspects[-1].method_name}' "
            f"(тип: {aspects[-1].aspect_type})."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация чекеров
# ═════════════════════════════════════════════════════════════════════════════


def validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[CheckerMeta],
    aspects: list[AspectMeta],
) -> None:
    """
    Проверяет, что каждый чекер привязан к существующему аспекту.

    Аргументы:
        cls: класс для сообщений об ошибках.
        checkers: собранные чекеры.
        aspects: собранные аспекты.

    Исключения:
        ValueError: если чекер привязан к несуществующему аспекту.
    """
    aspect_names = {a.method_name for a in aspects}

    for checker in checkers:
        if checker.method_name not in aspect_names:
            raise ValueError(
                f"Класс {cls.__name__}: чекер '{checker.checker_class.__name__}' "
                f"для поля '{checker.field_name}' привязан к методу "
                f"'{checker.method_name}', который не является аспектом. "
                f"Чекеры можно применять только к методам с @regular_aspect "
                f"или @summary_aspect."
            )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация обработчиков ошибок (@on_error)
# ═════════════════════════════════════════════════════════════════════════════


def _is_type_covered_by(
    candidate_type: type[Exception],
    covering_types: tuple[type[Exception], ...],
) -> bool:
    """
    Проверяет, перекрывается ли candidate_type одним из covering_types.

    Тип считается перекрытым, если он совпадает с одним из covering_types
    или является его подклассом. Это означает, что вышестоящий обработчик
    всегда перехватит исключение этого типа раньше.

    Аргументы:
        candidate_type: тип исключения нижестоящего обработчика.
        covering_types: типы исключений вышестоящего обработчика.

    Возвращает:
        True если candidate_type перекрыт covering_types.
    """
    for covering in covering_types:
        if issubclass(candidate_type, covering):
            return True
    return False


def validate_error_handlers(
    cls: type,
    error_handlers: list[OnErrorMeta],
) -> None:
    """
    Проверяет порядок обработчиков ошибок и отсутствие перекрытия типов.

    Инвариант: нижестоящий обработчик не может ловить типы исключений,
    которые уже перехватываются вышестоящим обработчиком (совпадающие
    или дочерние). Это защита от мёртвого кода — обработчик, который
    никогда не получит управления, является ошибкой разработчика.

    Допустимый порядок: сначала специфичные типы, потом общие.
        @on_error(ValueError, ...)      ← специфичный
        @on_error(Exception, ...)       ← общий fallback

    Недопустимый порядок: сначала общий, потом специфичный.
        @on_error(Exception, ...)       ← перехватит всё
        @on_error(ValueError, ...)      ← мёртвый код → TypeError

    Аргументы:
        cls: класс для сообщений об ошибках.
        error_handlers: собранные обработчики ошибок в порядке объявления.

    Исключения:
        TypeError: если обнаружено перекрытие типов.
    """
    if len(error_handlers) < 2:
        return

    for i in range(1, len(error_handlers)):
        current_handler = error_handlers[i]

        for j in range(i):
            upper_handler = error_handlers[j]

            for candidate_type in current_handler.exception_types:
                if _is_type_covered_by(candidate_type, upper_handler.exception_types):
                    covering_name = next(
                        c.__name__
                        for c in upper_handler.exception_types
                        if issubclass(candidate_type, c)
                    )
                    raise TypeError(
                        f"Класс {cls.__name__}: обработчик ошибок "
                        f"'{current_handler.method_name}' ловит "
                        f"{candidate_type.__name__}, но вышестоящий "
                        f"обработчик '{upper_handler.method_name}' уже "
                        f"перехватывает {covering_name}. Тип "
                        f"{candidate_type.__name__} является подклассом "
                        f"{covering_name} (или совпадает с ним), поэтому "
                        f"обработчик '{current_handler.method_name}' никогда "
                        f"не получит управления. Переместите более специфичный "
                        f"обработчик выше более общего."
                    )


# ═════════════════════════════════════════════════════════════════════════════
# Валидация подписок плагинов (@on)
# ═════════════════════════════════════════════════════════════════════════════


def _extract_event_annotation(cls: type, method_name: str) -> type | None:
    """
    Извлекает аннотацию типа параметра event из сигнатуры метода плагина.

    Обработчик плагина имеет сигнатуру (self, state, event, log).
    Параметр event — третий (индекс 2). Аннотация может быть конкретным
    классом (GlobalFinishEvent), групповым (AspectEvent) или базовым
    (BasePluginEvent).

    Если аннотация отсутствует или не является подклассом BasePluginEvent,
    возвращает None (проверка пропускается — аннотация необязательна).

    Аргументы:
        cls: класс плагина.
        method_name: имя метода-обработчика.

    Возвращает:
        type — аннотация параметра event (подкласс BasePluginEvent),
        или None если аннотация отсутствует или не является типом события.
    """
    # Ищем метод в MRO
    func = None
    for klass in cls.__mro__:
        if method_name in vars(klass):
            func = vars(klass)[method_name]
            break

    if func is None:
        return None

    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return None

    params_list = list(sig.parameters.values())
    # Параметр event — третий (self=0, state=1, event=2, log=3)
    if len(params_list) < 3:
        return None

    event_param = params_list[2]
    annotation = event_param.annotation

    if annotation is inspect.Parameter.empty:
        return None

    if isinstance(annotation, type) and issubclass(annotation, BasePluginEvent):
        return annotation

    return None


def validate_subscriptions(
    cls: type,
    subscriptions: list[SubscriptionInfo],
) -> None:
    """
    Проверяет совместимость подписок плагинов с аннотациями обработчиков.

    Для каждой подписки (SubscriptionInfo) проверяет: если метод-обработчик
    имеет аннотацию типа на параметре event, то event_class из @on должен
    быть подклассом этой аннотации (или совпадать с ней).

    Это гарантирует, что обработчик всегда получит событие, совместимое
    с аннотацией. Если аннотация — GlobalFinishEvent, а event_class —
    GlobalLifecycleEvent, обработчик может получить GlobalStartEvent,
    у которого нет полей GlobalFinishEvent (result, duration_ms).
    Это ошибка типизации, обнаруживаемая при сборке метаданных.

    Допустимые комбинации:
        @on(GlobalFinishEvent) + event: GlobalFinishEvent     — OK (совпадает)
        @on(GlobalFinishEvent) + event: GlobalLifecycleEvent  — OK (подкласс)
        @on(GlobalFinishEvent) + event: BasePluginEvent       — OK (подкласс)
        @on(GlobalLifecycleEvent) + event: GlobalFinishEvent  — ОШИБКА
        @on(AspectEvent) + event: AfterRegularAspectEvent     — ОШИБКА

    Если аннотация отсутствует — проверка пропускается для этой подписки.
    Один метод может иметь несколько @on (OR-семантика) — каждая подписка
    проверяется независимо.

    Аргументы:
        cls: класс плагина для сообщений об ошибках.
        subscriptions: собранные подписки (list[SubscriptionInfo]).

    Исключения:
        TypeError: если event_class несовместим с аннотацией event.
    """
    for sub in subscriptions:
        if not isinstance(sub, SubscriptionInfo):
            continue

        annotation = _extract_event_annotation(cls, sub.method_name)

        if annotation is None:
            # Аннотация отсутствует или не является типом события —
            # проверка пропускается.
            continue

        # event_class из @on должен быть подклассом аннотации.
        # Это гарантирует: если обработчик аннотирован GlobalFinishEvent,
        # он получит только GlobalFinishEvent (или его наследника),
        # а не GlobalStartEvent.
        if not issubclass(sub.event_class, annotation):
            raise TypeError(
                f"Класс {cls.__name__}: метод '{sub.method_name}' подписан "
                f"на {sub.event_class.__name__} через @on, но параметр event "
                f"аннотирован как {annotation.__name__}. Тип "
                f"{sub.event_class.__name__} не является подклассом "
                f"{annotation.__name__}, поэтому обработчик может получить "
                f"событие без ожидаемых полей. Измените аннотацию на "
                f"{sub.event_class.__name__} или более общий тип "
                f"(например, BasePluginEvent)."
            )
