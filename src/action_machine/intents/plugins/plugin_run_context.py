# src/action_machine/intents/plugins/plugin_run_context.py
"""
PluginRunContext — изолированный контекст плагинов для одного вызова run().

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

PluginRunContext инкапсулирует всё мутабельное состояние плагинов,
необходимое для одного вызова ActionProductMachine.run(). Каждый вызов
run() создаёт свой экземпляр PluginRunContext, который живёт ровно
столько, сколько длится выполнение действия, и уничтожается по завершении.

Это гарантирует полную изоляцию между запросами: состояния плагинов
одного run() не влияют на другой run(), даже при параллельном выполнении
в рамках одного event loop (asyncio.gather нескольких run()).

═══════════════════════════════════════════════════════════════════════════════
ТИПОБЕЗОПАСНАЯ ДОСТАВКА СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

Метод emit_event() принимает один аргумент — объект события из иерархии
BasePluginEvent. Машина (ActionProductMachine) создаёт конкретные объекты
событий (GlobalStartEvent, AfterRegularAspectEvent и т.д.) в ключевых
точках конвейера и передаёт их в emit_event(). Контекст находит
подходящие обработчики и доставляет им событие.

Каждый класс события содержит РОВНО те поля, которые имеют смысл для
данного типа. GlobalStartEvent не имеет result (результат ещё не известен),
AfterRegularAspectEvent содержит aspect_result и duration_ms. Это устраняет
проблему единого PluginEvent с Optional-полями, где большинство полей
равны None для конкретного события.

═══════════════════════════════════════════════════════════════════════════════
ЦЕПОЧКА ФИЛЬТРОВ ПРИ ЭМИССИИ СОБЫТИЯ
═══════════════════════════════════════════════════════════════════════════════

Когда emit_event() получает событие, он обходит все подписки всех плагинов
и для каждой подписки проверяет, нужно ли вызывать обработчик. Фильтры
проверяются последовательно, от самого дешёвого к самому дорогому.
Ранний выход на первом несовпадении — дорогие проверки не выполняются,
если дешёвая уже отсекла подписку.

    Событие приходит в emit_event()
             │
             ▼
    Шаг 1: isinstance(event, sub.event_class)?
             │  Дешёвая проверка — одна инструкция isinstance.
             │  Отсекает ~90% подписок сразу, потому что большинство
             │  плагинов подписаны на конкретные типы событий.
             │  НЕТ → пропускаем обработчик
             │
             ▼
    Шаг 2: action_class указан? → isinstance(action, sub.action_class)?
             │  Дешёвая проверка — isinstance.
             │  Отсекает подписки, ограниченные конкретными действиями.
             │  НЕТ → пропускаем
             │
             ▼
    Шаг 3: action_name_pattern указан? → re.search(pattern, event.action_name)?
             │  Дороже — выполнение предкомпилированного regex.
             │  Фильтрация по модулю или паттерну имени.
             │  НЕТ → пропускаем
             │
             ▼
    Шаг 4: aspect_name_pattern указан? → re.search(pattern, event.aspect_name)?
             │  Применяется только к AspectEvent и наследникам.
             │  Для не-аспектных событий пропускается.
             │  НЕТ → пропускаем
             │
             ▼
    Шаг 5: nest_level указан? → event.nest_level in sub.nest_level?
             │  Дешёвая проверка — сравнение int или in tuple.
             │  НЕТ → пропускаем
             │
             ▼
    Шаг 6: domain указан? → проверка через координатор метаданных
             │  Дороже — ``coordinator.get_snapshot(event.action_class, \"meta\")``.
             │  НЕТ → пропускаем
             │
             ▼
    Шаг 7: predicate указан? → predicate(event)?
             │  Самая дорогая — произвольная пользовательская функция.
             │  К моменту вызова гарантировано: isinstance(event, event_class).
             │  Обращение к специфичным полям event_class безопасно.
             │  НЕТ → пропускаем
             │
             ▼
    ВСЕ ФИЛЬТРЫ ПРОШЛИ → вызываем обработчик

Шаг 1 (isinstance по event_class) выполняется в Plugin.get_handlers(),
шаги 2–7 выполняются в PluginRunContext._matches_all_filters().

═══════════════════════════════════════════════════════════════════════════════
AND-ЛОГИКА ФИЛЬТРОВ ВНУТРИ ОДНОГО @on
═══════════════════════════════════════════════════════════════════════════════

Все фильтры в одном @on (одном SubscriptionInfo) проверяются совместно
с AND-логикой: обработчик вызывается, только если ВСЕ указанные фильтры
пройдены одновременно. Неуказанные фильтры (None) пропускаются.

Каждый фильтр СУЖАЕТ выборку. Разработчик говорит: «вызови меня для
GlobalFinishEvent И только для OrderAction И только на корневом уровне».
С OR-логикой nest_level=0 вызвал бы обработчик для ВСЕХ корневых
вызовов любых действий — не то, что нужно.

OR-логика реализуется МЕЖДУ несколькими @on на одном методе: метод
вызывается, если хотя бы одна подписка совпала. Каждый @on создаёт
отдельный SubscriptionInfo.

═══════════════════════════════════════════════════════════════════════════════
ФИЛЬТРАЦИЯ ПО ДОМЕНУ
═══════════════════════════════════════════════════════════════════════════════

Фильтр domain проверяется через GateCoordinator: для action_class
события запрашиваются метаданные, и из них извлекается domain.
GateCoordinator передаётся в PluginRunContext при создании. Это самый
дорогой фильтр после predicate, потому что требует обращения к кешу
координатора. Поэтому domain проверяется на шаге 6, после всех
дешёвых проверок.

═══════════════════════════════════════════════════════════════════════════════
PREDICATE И ТИПИЗАЦИЯ EVENT
═══════════════════════════════════════════════════════════════════════════════

Параметр predicate — произвольная функция фильтрации. Формальная
аннотация — Callable[[BasePluginEvent], bool]. Фактический тип event
в рантайме ГАРАНТИРОВАННО соответствует event_class из того же
декоратора, потому что predicate вызывается ПОСЛЕ проверки
isinstance(event, sub.event_class) на шаге 1. Поэтому обращение
к специфичным полям event_class в лямбде безопасно:

    @on(GlobalFinishEvent, predicate=lambda e: e.duration_ms > 1000)
    # e — GlobalFinishEvent в рантайме, доступ к duration_ms безопасен

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ ВЫПОЛНЕНИЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

После прохождения фильтров собранные обработчики выполняются по одной
из двух стратегий, выбираемой автоматически на основе флагов
ignore_exceptions:

1. ВСЕ обработчики имеют ignore_exceptions=True:
   Запуск параллельно через asyncio.gather(return_exceptions=True).
   Общее время ≈ время самого медленного обработчика. Падающие
   обработчики не прерывают остальных — их исключения подавляются; при
   переданном log_coordinator для каждого сбоя пишется CRITICAL в Channel.error.

2. ХОТЯ БЫ ОДИН обработчик имеет ignore_exceptions=False:
   Запуск последовательно. Общее время ≈ сумма всех задержек.
   При ошибке критического обработчика (ignore_exceptions=False)
   исключение пробрасывается наружу и прерывает выполнение.

═══════════════════════════════════════════════════════════════════════════════
ЛОГГЕР ДЛЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов получают ScopedLogger как параметр log.
PluginRunContext создаёт ScopedLogger для каждого вызова обработчика
со scope: machine, mode, plugin, action, event, nest_level и с
``domain=resolve_domain(event.action_class)`` (см. ``_create_plugin_logger``).

Поля scope доступны в шаблонах логирования через {%scope.*}:
    from action_machine.intents.logging.channel import Channel

    await log.info(
        Channel.debug,
        "[{%scope.plugin}] Действие {%scope.action} завершено",
    )

Для создания ScopedLogger требуются log_coordinator, machine_name и mode,
которые передаются в emit_event() из машины через именованные аргументы;
домен задаётся из класса действия события, как указано выше.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal(...)
        │
        │  event = GlobalStartEvent(action_class=..., ...)
        │  await plugin_ctx.emit_event(event, coordinator=..., ...)
        ▼
    PluginRunContext.emit_event(event, ...)
        │
        │  Для каждого плагина:
        │    handlers = plugin.get_handlers(event)  ← Шаг 1: event_class
        │    Для каждого (handler, sub):
        │      _matches_all_filters(event, sub)     ← Шаги 2–7
        │      → собираем прошедших в список
        │
        │  Выбираем стратегию выполнения:
        │    все ignore=True → параллельно (asyncio.gather)
        │    иначе → последовательно
        │
        │  Для каждого прошедшего обработчика:
        │    создаём ScopedLogger с scope плагина
        │    state = await handler(plugin, state, event, log)
        │    обновляем _plugin_states[id(plugin)]
        ▼

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # В ActionProductMachine:
    event = GlobalFinishEvent(
        action_class=type(action),
        action_name=action.get_full_class_name(),
        nest_level=current_nest,
        context=context,
        params=params,
        result=result,
        duration_ms=total_duration * 1000,
    )
    await plugin_ctx.emit_event(
        event,
        log_coordinator=self._log_coordinator,
        machine_name=self.__class__.__name__,
        mode=self._mode,
        coordinator=self._coordinator,
    )
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.intents.logging.channel import Channel
from action_machine.intents.logging.domain_resolver import resolve_domain
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.logging.scoped_logger import ScopedLogger
from action_machine.intents.plugins.events import BasePluginEvent
from action_machine.intents.plugins.plugin import Plugin
from action_machine.intents.plugins.subscription_info import SubscriptionInfo
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState


class PluginRunContext:
    """
    Изолированный контекст плагинов для одного вызова run().

    Создаётся методом PluginCoordinator.create_run_context() в начале
    каждого _run_internal(). Хранит состояния всех плагинов и предоставляет
    метод emit_event() для доставки типизированных событий обработчикам
    через цепочку фильтров.

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов (ссылка на список из координатора).

        _plugin_states : dict[int, Any]
            Состояния плагинов для текущего запроса. Ключ — id(plugin),
            значение — текущее состояние (обновляется после каждого
            вызова обработчика).
    """

    def __init__(
        self,
        plugins: list[Plugin],
        initial_states: dict[int, Any],
    ) -> None:
        """
        Инициализирует контекст плагинов.

        Аргументы:
            plugins: список экземпляров плагинов.
            initial_states: начальные состояния плагинов.
                Ключ — id(plugin), значение — результат get_initial_state().
        """
        self._plugins: list[Plugin] = plugins
        self._plugin_states: dict[int, Any] = dict(initial_states)

    # ─────────────────────────────────────────────────────────────────────
    # Фильтрация подписок (шаги 2–7 цепочки)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _matches_all_filters(  # pylint: disable=too-many-return-statements
        event: BasePluginEvent,
        sub: SubscriptionInfo,
        coordinator: Any | None = None,
    ) -> bool:
        """
        Проверяет фильтры подписки (шаги 2–7 цепочки).

        Шаг 1 (isinstance по event_class) уже выполнен в
        Plugin.get_handlers(). Здесь проверяются остальные фильтры
        в порядке от дешёвых к дорогим с ранним выходом.

        Порядок проверки:
            Шаг 2: action_class → isinstance
            Шаг 3: action_name_pattern → предкомпилированный regex
            Шаг 4: aspect_name_pattern → предкомпилированный regex
            Шаг 5: nest_level → in tuple
            Шаг 6: domain → обращение к GateCoordinator
            Шаг 7: predicate → вызов пользовательской функции

        Аргументы:
            event: объект события.
            sub: подписка (SubscriptionInfo) для проверки.
            coordinator: GateCoordinator для проверки domain (или None).

        Возвращает:
            True если все указанные фильтры прошли.
        """
        # ── Шаг 2: action_class ──
        if sub.action_class is not None:
            if not isinstance(event.action_class, type):
                return False
            # Проверяем, что action_class события является подклассом
            # одного из классов в фильтре (или совпадает).
            if not issubclass(event.action_class, sub.action_class):
                return False

        # ── Шаг 3: action_name_pattern ──
        if not sub.matches_action_name(event.action_name):
            return False

        # ── Шаг 4: aspect_name_pattern ──
        if not sub.matches_aspect_name(event):
            return False

        # ── Шаг 5: nest_level ──
        if not sub.matches_nest_level(event.nest_level):
            return False

        # ── Шаг 6: domain ──
        if sub.domain is not None and coordinator is not None:
            try:
                m = coordinator.get_snapshot(event.action_class, "meta")
                action_domain = m.domain if m is not None else None
                if action_domain is not sub.domain:
                    return False
            except Exception:
                return False

        # ── Шаг 7: predicate ──
        if not sub.matches_predicate(event):
            return False

        return True

    # ─────────────────────────────────────────────────────────────────────
    # Сбор подходящих обработчиков
    # ─────────────────────────────────────────────────────────────────────

    def _collect_matched_handlers(
        self,
        event: BasePluginEvent,
        coordinator: Any | None = None,
    ) -> list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]]:
        """
        Собирает все обработчики, прошедшие полную цепочку фильтров.

        Для каждого плагина вызывает plugin.get_handlers(event) (шаг 1),
        затем для каждого кандидата проверяет шаги 2–7 через
        _matches_all_filters().

        Аргументы:
            event: объект события.
            coordinator: GateCoordinator для фильтра domain (или None).

        Возвращает:
            Список кортежей (plugin, handler, subscription).
        """
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]] = []

        for plugin in self._plugins:
            candidates = plugin.get_handlers(event)

            for handler, sub in candidates:
                if self._matches_all_filters(event, sub, coordinator):
                    matched.append((plugin, handler, sub))

        return matched

    # ─────────────────────────────────────────────────────────────────────
    # Создание ScopedLogger для обработчика плагина
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _create_plugin_logger(
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        plugin: Plugin,
        event: BasePluginEvent,
    ) -> ScopedLogger | None:
        """
        Создаёт ScopedLogger для обработчика плагина.

        ``domain=resolve_domain(event.action_class)``. Scope содержит поля:
        machine, mode, plugin, action, event (имя типа события), nest_level.
        Все поля доступны в шаблонах через {%scope.*}.

        Аргументы:
            log_coordinator: координатор логирования (или None).
            machine_name: имя класса машины.
            mode: режим выполнения.
            plugin: экземпляр плагина.
            event: объект события.

        Возвращает:
            ScopedLogger или None если log_coordinator не указан.
        """
        if log_coordinator is None:
            return None

        return ScopedLogger(
            coordinator=log_coordinator,
            nest_level=event.nest_level,
            machine_name=machine_name,
            mode=mode,
            action_name=event.action_name,
            aspect_name="",
            context=event.context,
            state=BaseState(),
            params=event.params if isinstance(event.params, BaseParams) else BaseParams(),
            plugin_name=type(plugin).__name__,
            event_name=type(event).__name__,
            domain=resolve_domain(event.action_class),
        )

    @staticmethod
    async def _log_suppressed_handler_exception(
        exc: Exception,
        log: ScopedLogger | None,
        method_name: str,
    ) -> None:
        if log is None:
            return
        await log.critical(
            Channel.error,
            "Plugin handler {%var.handler_name} failed and was suppressed "
            "(ignore_exceptions=True): {%var.exc_type}: {%var.exc_message}",
            handler_name=method_name,
            exc_type=type(exc).__name__,
            exc_message=str(exc),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Выполнение одного обработчика
    # ─────────────────────────────────────────────────────────────────────

    async def _run_single_handler(
        self,
        plugin: Plugin,
        handler: Callable[..., Any],
        event: BasePluginEvent,
        log: ScopedLogger | None,
    ) -> None:
        """
        Вызывает один обработчик плагина и обновляет per-request состояние.

        Получает текущее состояние из _plugin_states, вызывает обработчик,
        записывает обновлённое состояние обратно.

        Аргументы:
            plugin: экземпляр плагина.
            handler: unbound-метод обработчика.
            event: объект события.
            log: ScopedLogger для обработчика (или None).
        """
        plugin_id = id(plugin)
        state = self._plugin_states.get(plugin_id)

        new_state = await handler(plugin, state, event, log)

        self._plugin_states[plugin_id] = new_state

    # ─────────────────────────────────────────────────────────────────────
    # Стратегии выполнения: параллельная и последовательная
    # ─────────────────────────────────────────────────────────────────────

    async def _run_parallel(
        self,
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]],
        event: BasePluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
    ) -> None:
        """
        Параллельное выполнение обработчиков через asyncio.gather.

        Используется когда ВСЕ обработчики имеют ignore_exceptions=True.
        Общее время ≈ время самого медленного обработчика. Исключения
        подавляются (return_exceptions=True); при непустом log_coordinator
        для каждого сбоя пишется CRITICAL в Channel.error.

        Аргументы:
            matched: список (plugin, handler, subscription).
            event: объект события.
            log_coordinator: координатор логирования.
            machine_name: имя класса машины.
            mode: режим выполнения.
        """
        tasks = []
        for plugin, handler, _sub in matched:
            log = self._create_plugin_logger(
                log_coordinator, machine_name, mode, plugin, event,
            )
            tasks.append(
                self._run_single_handler(plugin, handler, event, log)
            )

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (plugin, _handler, sub), result in zip(matched, results, strict=True):
                if isinstance(result, Exception):
                    log = self._create_plugin_logger(
                        log_coordinator, machine_name, mode, plugin, event,
                    )
                    await self._log_suppressed_handler_exception(
                        result, log, sub.method_name,
                    )

    async def _run_sequential(
        self,
        matched: list[tuple[Plugin, Callable[..., Any], SubscriptionInfo]],
        event: BasePluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
    ) -> None:
        """
        Последовательное выполнение обработчиков.

        Используется когда ХОТЯ БЫ ОДИН обработчик имеет
        ignore_exceptions=False. При ошибке критического обработчика
        исключение пробрасывается наружу. Ошибки обработчиков
        с ignore_exceptions=True подавляются; при непустом log_coordinator
        для такого сбоя пишется CRITICAL в Channel.error.

        Аргументы:
            matched: список (plugin, handler, subscription).
            event: объект события.
            log_coordinator: координатор логирования.
            machine_name: имя класса машины.
            mode: режим выполнения.
        """
        for plugin, handler, sub in matched:
            log = self._create_plugin_logger(
                log_coordinator, machine_name, mode, plugin, event,
            )
            try:
                await self._run_single_handler(plugin, handler, event, log)
            except Exception as exc:
                if not sub.ignore_exceptions:
                    raise
                await self._log_suppressed_handler_exception(
                    exc, log, sub.method_name,
                )

    # ─────────────────────────────────────────────────────────────────────
    # Основной метод: emit_event
    # ─────────────────────────────────────────────────────────────────────

    async def emit_event(
        self,
        event: BasePluginEvent,
        *,
        log_coordinator: LogCoordinator | None = None,
        machine_name: str = "",
        mode: str = "",
        coordinator: Any | None = None,
    ) -> None:
        """
        Доставляет типизированное событие всем подходящим обработчикам.

        Принимает объект события из иерархии BasePluginEvent. Находит
        все обработчики, прошедшие полную цепочку фильтров (7 шагов),
        выбирает стратегию выполнения (параллельная или последовательная)
        и запускает обработчики.

        Цепочка фильтров:
            Шаг 1: event_class (isinstance) — в Plugin.get_handlers()
            Шаг 2: action_class (isinstance)
            Шаг 3: action_name_pattern (regex)
            Шаг 4: aspect_name_pattern (regex, только AspectEvent)
            Шаг 5: nest_level (in tuple)
            Шаг 6: domain (через GateCoordinator)
            Шаг 7: predicate (пользовательская функция)

        Стратегия выполнения:
            Все ignore_exceptions=True → параллельно (asyncio.gather).
            Хотя бы один ignore_exceptions=False → последовательно.

        Аргументы:
            event: объект события из иерархии BasePluginEvent.
                Машина создаёт конкретные события (GlobalStartEvent,
                AfterRegularAspectEvent и т.д.) и передаёт сюда.

            log_coordinator: координатор логирования для создания
                ScopedLogger обработчикам. None — логирование недоступно.

            machine_name: имя класса машины (для scope логгера).
                Пример: "ActionProductMachine".

            mode: режим выполнения (для scope логгера).
                Пример: "production", "test".

            coordinator: GateCoordinator для проверки фильтра domain.
                None — фильтр domain пропускается.

        Исключения:
            Любое исключение из обработчика с ignore_exceptions=False
            пробрасывается наружу.
        """
        # ── Сбор обработчиков, прошедших все фильтры ──
        matched = self._collect_matched_handlers(event, coordinator)

        if not matched:
            return

        # ── Выбор стратегии выполнения ──
        all_ignore = all(sub.ignore_exceptions for _, _, sub in matched)

        if all_ignore:
            await self._run_parallel(
                matched, event, log_coordinator, machine_name, mode,
            )
        else:
            await self._run_sequential(
                matched, event, log_coordinator, machine_name, mode,
            )

    # ─────────────────────────────────────────────────────────────────────
    # Доступ к состоянию плагина (для тестов и интроспекции)
    # ─────────────────────────────────────────────────────────────────────

    def get_plugin_state(self, plugin: Plugin) -> Any:
        """
        Возвращает текущее per-request состояние плагина.

        Используется в тестах для проверки, что обработчик корректно
        обновил состояние. В production-коде не вызывается — состояние
        инкапсулировано внутри контекста.

        Аргументы:
            plugin: экземпляр плагина.

        Возвращает:
            Текущее состояние плагина.

        Исключения:
            KeyError: если плагин не зарегистрирован в контексте.
        """
        return self._plugin_states[id(plugin)]
