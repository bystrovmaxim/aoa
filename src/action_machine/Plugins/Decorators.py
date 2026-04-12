# src/action_machine/plugins/decorators.py
"""
Декоратор @on — подписка метода плагина на событие машины.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on — часть грамматики намерений ActionMachine для плагинов.
Он объявляет, что метод плагина должен вызываться при наступлении
определённого события. Машина (ActionProductMachine) создаёт конкретные
объекты событий (GlobalStartEvent, AfterRegularAspectEvent и т.д.)
в ключевых точках конвейера, а PluginRunContext доставляет их
обработчикам, чьи подписки прошли цепочку фильтров.

═══════════════════════════════════════════════════════════════════════════════
ТИПОБЕЗОПАСНАЯ ПОДПИСКА ЧЕРЕЗ КЛАССЫ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

Первый параметр event_class — тип события из иерархии BasePluginEvent.
Подписка срабатывает для event_class и всех его наследников через
isinstance-проверку в PluginRunContext:

    @on(BasePluginEvent)              — все события системы
    @on(GlobalLifecycleEvent)         — global_start + global_finish
    @on(GlobalFinishEvent)            — только global_finish
    @on(AspectEvent)                  — все before/after всех типов аспектов
    @on(RegularAspectEvent)           — before + after regular-аспектов
    @on(AfterRegularAspectEvent)      — только after regular-аспектов

Опечатка в имени класса → ImportError при импорте модуля, а не
молчаливый баг в рантайме. IDE автодополняет имена классов.

═══════════════════════════════════════════════════════════════════════════════
ФИЛЬТРЫ — AND-ЛОГИКА ВНУТРИ ОДНОГО @on
═══════════════════════════════════════════════════════════════════════════════

Все фильтры в одном @on проверяются совместно (AND-логика): обработчик
вызывается, только если ВСЕ указанные фильтры пройдены одновременно.
Неуказанные фильтры (None) пропускаются.

    @on(
        GlobalFinishEvent,
        action_class=CreateOrderAction,     # И тип действия совпадает
        nest_level=0,                       # И это корневой вызов
        predicate=lambda e: e.duration_ms > 1000,  # И выполнение > 1с
    )

═══════════════════════════════════════════════════════════════════════════════
OR-ЛОГИКА МЕЖДУ НЕСКОЛЬКИМИ @on НА ОДНОМ МЕТОДЕ
═══════════════════════════════════════════════════════════════════════════════

Несколько @on на одном методе — OR-семантика: обработчик вызывается,
если хотя бы одна подписка совпала:

    @on(GlobalStartEvent)               # ИЛИ start
    @on(GlobalFinishEvent)              # ИЛИ finish
    async def on_lifecycle(self, state, event: GlobalLifecycleEvent, log):
        ...

Каждый @on создаёт отдельный SubscriptionInfo. PluginRunContext проверяет
каждую подписку независимо.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКА
═══════════════════════════════════════════════════════════════════════════════

Все обработчики обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event: EventClass, log) -> state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина (dict или другой объект).
    - event  — объект события. Аннотация типа может быть конкретным классом
               (GlobalFinishEvent), групповым (AspectEvent) или базовым
               (BasePluginEvent). MetadataBuilder проверяет совместимость:
               event_class из @on должен быть подклассом аннотации event.
    - log    — ScopedLogger, привязанный к scope плагина.

Обработчик обязан вернуть обновлённое состояние.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура метода: ровно 4 параметра (self, state, event, log).
- Имя метода обязано начинаться с "on_" (проверяется NamingPrefixError).
- event_class — обязательный, подкласс BasePluginEvent.
- action_class — None, type или tuple[type, ...].
- action_name_pattern — None или строка (валидный regex).
- aspect_name_pattern — None или строка (валидный regex). Применим
  ТОЛЬКО к наследникам AspectEvent. Для не-аспектных event_class →
  ValueError при создании SubscriptionInfo.
- nest_level — None, int или tuple[int, ...].
- domain — None или type (подкласс BaseDomain).
- predicate — None или callable.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @on(GlobalFinishEvent, action_class=OrderAction, nest_level=0)
        │
        ▼  Декоратор создаёт SubscriptionInfo и добавляет в method._on_subscriptions
    SubscriptionInfo(
        event_class=GlobalFinishEvent,
        action_class=(OrderAction,),
        nest_level=(0,),
        method_name="on_order_finish",
        ...
    )
        │
        ▼  collect_subscriptions в MetadataBuilder (валидация)
        ▼  GateCoordinator.get_subscriptions() — снимок
        │
        ▼  MetadataBuilder → on_intent.validate_subscriptions(cls, ...)
    Проверка совместимости event_class ↔ аннотация event параметра
        │
        ▼  PluginRunContext.emit_event(event)
    Для каждой подписки: цепочка фильтров → вызов обработчика

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.logging.channel import Channel
    from action_machine.plugins.events import (
        GlobalFinishEvent,
        AfterRegularAspectEvent,
        AspectEvent,
        UnhandledErrorEvent,
    )

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"slow_count": 0, "errors": []}

        # Конкретное событие, фильтр по длительности
        @on(
            GlobalFinishEvent,
            predicate=lambda e: e.duration_ms > 1000,
        )
        async def on_slow_actions(self, state, event: GlobalFinishEvent, log):
            state["slow_count"] += 1
            await log.warning(
                Channel.business,
                "Медленное действие: {%var.name} за {%var.ms}мс",
                name=event.action_name,
                ms=event.duration_ms,
            )
            return state

        # Групповое событие — все аспекты
        @on(AspectEvent)
        async def on_any_aspect(self, state, event: AspectEvent, log):
            await log.info(Channel.debug, "Аспект: {%var.name}", name=event.aspect_name)
            return state

        # Фильтр по типу аспекта и имени
        @on(
            AfterRegularAspectEvent,
            aspect_name_pattern=r"validate_.*",
            nest_level=0,
        )
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            return state

        # Ошибки без обработчика
        @on(UnhandledErrorEvent)
        async def on_unhandled(self, state, event: UnhandledErrorEvent, log):
            state["errors"].append(str(event.error))
            return state

        # OR-семантика: два @on на одном методе
        @on(GlobalFinishEvent, action_class=OrderAction)
        @on(GlobalFinishEvent, action_class=PaymentAction)
        async def on_business_finish(self, state, event: GlobalFinishEvent, log):
            return state

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — event_class не подкласс BasePluginEvent; метод не callable;
               метод не асинхронный; неверное число параметров (не 4);
               action_class не type и не tuple[type]; domain не type.
    ValueError — aspect_name_pattern для не-аспектного event_class;
                невалидный regex; nest_level отрицательный.
    NamingPrefixError — имя метода не начинается с "on_".
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.core.exceptions import NamingPrefixError
from action_machine.plugins.events import BasePluginEvent
from action_machine.plugins.subscription_info import SubscriptionInfo

# Ожидаемое число параметров для @on: self, state, event, log
_EXPECTED_PARAM_COUNT = 4

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, state, event, log"

# Обязательная приставка имени метода
_REQUIRED_PREFIX = "on_"


# ═════════════════════════════════════════════════════════════════════════════
# Валидация аргументов декоратора
# ═════════════════════════════════════════════════════════════════════════════


def _validate_event_class(event_class: Any) -> None:
    """
    Проверяет, что event_class — подкласс BasePluginEvent.

    Аргументы:
        event_class: значение первого аргумента @on.

    Исключения:
        TypeError: если event_class не type или не подкласс BasePluginEvent.
    """
    if not isinstance(event_class, type) or not issubclass(
        event_class, BasePluginEvent
    ):
        raise TypeError(
            f"@on: первый аргумент event_class должен быть подклассом "
            f"BasePluginEvent, получен {event_class!r}. "
            f"Пример: @on(GlobalFinishEvent)"
        )


def _normalize_action_class(
    action_class: type | tuple[type, ...] | None,
) -> tuple[type, ...] | None:
    """
    Нормализует action_class в кортеж типов или None.

    Аргументы:
        action_class: один тип, кортеж типов или None.

    Возвращает:
        tuple[type, ...] или None.

    Исключения:
        TypeError: если action_class не type, не tuple[type] и не None.
    """
    if action_class is None:
        return None

    if isinstance(action_class, type):
        return (action_class,)

    if isinstance(action_class, tuple):
        for i, item in enumerate(action_class):
            if not isinstance(item, type):
                raise TypeError(
                    f"@on: элемент action_class[{i}] должен быть типом, "
                    f"получен {type(item).__name__}: {item!r}."
                )
        return action_class

    raise TypeError(
        f"@on: action_class должен быть типом, кортежем типов или None, "
        f"получен {type(action_class).__name__}: {action_class!r}."
    )


def _validate_string_or_none(value: Any, param_name: str) -> None:
    """
    Проверяет, что значение — строка или None.

    Аргументы:
        value: проверяемое значение.
        param_name: имя параметра для сообщения об ошибке.

    Исключения:
        TypeError: если value не str и не None.
    """
    if value is not None and not isinstance(value, str):
        raise TypeError(
            f"@on: {param_name} должен быть строкой или None, "
            f"получен {type(value).__name__}: {value!r}."
        )


def _normalize_nest_level(
    nest_level: int | tuple[int, ...] | None,
) -> tuple[int, ...] | None:
    """
    Проверяет корректность nest_level.

    Нормализует ``int`` в ``tuple[int]`` и проверяет неотрицательность.

    Аргументы:
        nest_level: значение параметра.

    Возвращает:
        Кортеж уровней вложенности либо ``None``.

    Исключения:
        TypeError: если nest_level не int, не tuple[int] и не None.
        ValueError: если значение отрицательное.
    """
    if nest_level is None:
        return None

    if isinstance(nest_level, int):
        if nest_level < 0:
            raise ValueError(
                f"@on: nest_level не может быть отрицательным, "
                f"получено {nest_level}."
            )
        return (nest_level,)

    if isinstance(nest_level, tuple):
        for i, item in enumerate(nest_level):
            if not isinstance(item, int):
                raise TypeError(
                    f"@on: элемент nest_level[{i}] должен быть int, "
                    f"получен {type(item).__name__}: {item!r}."
                )
            if item < 0:
                raise ValueError(
                    f"@on: элемент nest_level[{i}] не может быть "
                    f"отрицательным, получено {item}."
                )
        return nest_level

    raise TypeError(
        f"@on: nest_level должен быть int, tuple[int, ...] или None, "
        f"получен {type(nest_level).__name__}: {nest_level!r}."
    )


def _validate_domain(domain: Any) -> None:
    """
    Проверяет, что domain — type или None.

    Аргументы:
        domain: значение параметра.

    Исключения:
        TypeError: если domain не type и не None.
    """
    if domain is not None and not isinstance(domain, type):
        raise TypeError(
            f"@on: domain должен быть классом домена или None, "
            f"получен {type(domain).__name__}: {domain!r}."
        )


def _validate_predicate(predicate: Any) -> None:
    """
    Проверяет, что predicate — callable или None.

    Аргументы:
        predicate: значение параметра.

    Исключения:
        TypeError: если predicate не callable и не None.
    """
    if predicate is not None and not callable(predicate):
        raise TypeError(
            f"@on: predicate должен быть callable или None, "
            f"получен {type(predicate).__name__}: {predicate!r}."
        )


def _validate_method(func: Any, event_class_name: str) -> None:
    """
    Проверяет, что декорируемый объект — асинхронный метод с правильной
    сигнатурой и приставкой имени.

    Аргументы:
        func: декорируемый объект.
        event_class_name: имя event_class для сообщений об ошибках.

    Исключения:
        TypeError: если func не callable; не async; неверное число параметров.
        NamingPrefixError: если имя метода не начинается с "on_".
    """
    if not callable(func):
        raise TypeError(
            f"@on можно применять только к методам. "
            f"Получен объект типа {type(func).__name__}: {func!r}."
        )

    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@on({event_class_name}): метод {func.__name__} "
            f"должен быть асинхронным (async def). "
            f"Синхронные обработчики не поддерживаются."
        )

    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    if param_count != _EXPECTED_PARAM_COUNT:
        raise TypeError(
            f"@on({event_class_name}): метод {func.__name__} "
            f"должен принимать {_EXPECTED_PARAM_COUNT} параметра "
            f"({_EXPECTED_PARAM_NAMES}), получено {param_count}."
        )

    if not func.__name__.startswith(_REQUIRED_PREFIX):
        raise NamingPrefixError(
            f"@on({event_class_name}): метод '{func.__name__}' "
            f"должен начинаться с '{_REQUIRED_PREFIX}'. "
            f"Переименуйте в '{_REQUIRED_PREFIX}{func.__name__}' "
            f"или аналогичное имя с приставкой '{_REQUIRED_PREFIX}'."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def on(
    event_class: type[BasePluginEvent],
    *,
    action_class: type | tuple[type, ...] | None = None,
    action_name_pattern: str | None = None,
    aspect_name_pattern: str | None = None,
    nest_level: int | tuple[int, ...] | None = None,
    domain: type | None = None,
    predicate: Callable[[BasePluginEvent], bool] | None = None,
    ignore_exceptions: bool = True,
) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Подписывает метод плагина на событие машины.

    Создаёт SubscriptionInfo с указанными фильтрами и добавляет в
    атрибут method._on_subscriptions. Один метод может иметь несколько
    @on (несколько подписок с OR-семантикой между ними).

    Все обработчики обязаны иметь сигнатуру:
        async def handler(self, state, event: EventClass, log) -> state

    Имя метода обязано начинаться с "on_".

    Аргументы:
        event_class: тип события из иерархии BasePluginEvent. Обязательный.
            Подписка срабатывает для event_class и всех наследников.

        action_class: фильтр по типу действия. None — без фильтрации.
            Один тип или кортеж типов. isinstance-проверка покрывает
            иерархию наследования.

        action_name_pattern: regex по полному строковому имени действия.
            None — без фильтрации. re.search (совпадение в любом месте).

        aspect_name_pattern: regex по имени аспекта. None — без фильтрации.
            Применим ТОЛЬКО к наследникам AspectEvent. Для не-аспектных
            event_class — ValueError при создании SubscriptionInfo.

        nest_level: фильтр по уровню вложенности. None — без фильтрации.
            int — конкретный уровень. tuple[int, ...] — набор уровней.

        domain: фильтр по бизнес-домену действия. None — без фильтрации.

        predicate: произвольная функция фильтрации. None — без фильтрации.
            Вызывается ПОСЛЕ проверки isinstance(event, event_class),
            поэтому обращение к полям event_class безопасно.

        ignore_exceptions: подавление ошибок обработчика. True по умолчанию.

    Возвращает:
        Декоратор, который добавляет SubscriptionInfo в method._on_subscriptions
        и возвращает метод без изменений.

    Исключения:
        TypeError: event_class не подкласс BasePluginEvent; action_class
            неверного типа; метод не callable; не async; неверное число
            параметров; domain не type.
        ValueError: aspect_name_pattern для не-аспектного event_class;
            невалидный regex; nest_level отрицательный.
        NamingPrefixError: имя метода не начинается с "on_".
    """
    # ── Валидация аргументов декоратора ──
    _validate_event_class(event_class)
    normalized_action_class = _normalize_action_class(action_class)
    _validate_string_or_none(action_name_pattern, "action_name_pattern")
    _validate_string_or_none(aspect_name_pattern, "aspect_name_pattern")
    validated_nest_level = _normalize_nest_level(nest_level)
    _validate_domain(domain)
    _validate_predicate(predicate)

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к методу плагина.

        Проверяет callable, async, количество параметров, приставку имени.
        Создаёт SubscriptionInfo и добавляет в func._on_subscriptions.
        """
        _validate_method(func, event_class.__name__)

        # Создание SubscriptionInfo с валидацией в __post_init__
        # (компиляция regex, проверка aspect_name_pattern для AspectEvent)
        subscription = SubscriptionInfo(
            event_class=event_class,
            method_name=func.__name__,
            action_class=normalized_action_class,
            action_name_pattern=action_name_pattern,
            aspect_name_pattern=aspect_name_pattern,
            nest_level=validated_nest_level,
            domain=domain,
            predicate=predicate,
            ignore_exceptions=ignore_exceptions,
        )

        if not hasattr(func, "_on_subscriptions"):
            func._on_subscriptions = []

        func._on_subscriptions.append(subscription)

        return func

    return decorator
