# src/action_machine/plugins/subscription_info.py
"""
SubscriptionInfo — frozen-датакласс конфигурации одной подписки плагина.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

SubscriptionInfo хранит полную конфигурацию одной подписки метода плагина
на событие. Создаётся декоратором @on при определении класса плагина и
сохраняется в атрибуте method._on_subscriptions. Снимок подписок —
``GateCoordinator.get_subscriptions()`` (``SubscriptionGateHostInspector.Snapshot``).
PluginRunContext использует их для маршрутизации событий к обработчикам.

Один метод плагина может иметь несколько подписок (несколько @on),
каждая представлена отдельным SubscriptionInfo. Между подписками одного
метода действует OR-логика: обработчик вызывается, если хотя бы одна
подписка совпала. Внутри одной подписки действует AND-логика: все
указанные фильтры должны пройти одновременно.

═══════════════════════════════════════════════════════════════════════════════
ФИЛЬТРЫ И ИХ СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

Каждый фильтр — опциональный. Значение None означает «без фильтрации
по этому критерию» (пропускает любое значение). Фильтры проверяются
последовательно в PluginRunContext, от дешёвых к дорогим, с ранним
выходом при первом несовпадении.

Порядок проверки фильтров:

    1. event_class        — isinstance(event, event_class)
    2. action_class       — isinstance(action, action_class)
    3. action_name_pattern — re.search(pattern, event.action_name)
    4. aspect_name_pattern — re.search(pattern, event.aspect_name)
    5. nest_level         — event.nest_level in nest_level
    6. domain             — ``coordinator.get_snapshot(action_class, "meta").domain`` is domain
    7. predicate          — predicate(event)

═══════════════════════════════════════════════════════════════════════════════
КОМПИЛЯЦИЯ REGEX
═══════════════════════════════════════════════════════════════════════════════

Поля action_name_pattern и aspect_name_pattern хранят исходные строки
regex. Компилированные паттерны (re.Pattern) кешируются в полях
_compiled_action_name_pattern и _compiled_aspect_name_pattern через
object.__setattr__ в __post_init__ (обход frozen). Это обеспечивает
однократную компиляцию при создании подписки и быстрое выполнение
при каждой проверке в PluginRunContext.

Невалидный regex обнаруживается при компиляции в __post_init__
и вызывает ValueError с информативным сообщением. Ошибка возникает
при определении класса (когда применяется декоратор @on), а не
при обработке первого запроса.

═══════════════════════════════════════════════════════════════════════════════
НОРМАЛИЗАЦИЯ nest_level
═══════════════════════════════════════════════════════════════════════════════

Поле nest_level нормализуется в __post_init__:
    - None → None (без фильтрации).
    - int → tuple[int] (единственное значение → кортеж из одного элемента).
    - tuple[int, ...] → без изменений.

Это упрощает проверку в PluginRunContext: всегда
``event.nest_level in sub.nest_level`` без дополнительных isinstance.

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ aspect_name_pattern
═══════════════════════════════════════════════════════════════════════════════

Фильтр aspect_name_pattern применим ТОЛЬКО к событиям, являющимся
наследниками AspectEvent (событиям, имеющим поле aspect_name).
Если aspect_name_pattern указан, а event_class не является подклассом
AspectEvent — это ошибка конфигурации, обнаруживаемая в __post_init__
через проверку issubclass(event_class, AspectEvent).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР СОЗДАНИЯ (декоратором @on)
═══════════════════════════════════════════════════════════════════════════════

    # Декоратор @on создаёт SubscriptionInfo:
    sub = SubscriptionInfo(
        event_class=GlobalFinishEvent,
        action_class=(CreateOrderAction,),
        action_name_pattern=r"orders\\..*",
        aspect_name_pattern=None,
        nest_level=(0,),
        domain=OrdersDomain,
        predicate=lambda e: e.duration_ms > 1000,
        ignore_exceptions=True,
        method_name="on_slow_order_finish",
    )
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.plugins.events import AspectEvent, BasePluginEvent


@dataclass(frozen=True)
class SubscriptionInfo:
    """
    Frozen-датакласс конфигурации одной подписки плагина на событие.

    Создаётся декоратором @on и хранится в method._on_subscriptions.
    ``collect_subscriptions`` в билдере валидирует; рантайм — ``get_subscriptions``.
    PluginRunContext проверяет фильтры каждой подписки при эмиссии события.

    Все поля, кроме event_class и method_name, опциональны. None означает
    «без фильтрации по этому критерию».

    Кешированные атрибуты (создаются в __post_init__ через object.__setattr__):
        _compiled_action_name_pattern : re.Pattern | None
            Компилированный regex для action_name_pattern.
        _compiled_aspect_name_pattern : re.Pattern | None
            Компилированный regex для aspect_name_pattern.

    Атрибуты:
        event_class: тип события для подписки. Обязательный.
            Подписка срабатывает для event_class и всех его наследников
            через isinstance-проверку. Примеры:
                GlobalFinishEvent — только global_finish.
                GlobalLifecycleEvent — start + finish.
                AspectEvent — все аспектные события.
                BasePluginEvent — все события системы.

        action_class: фильтр по типу действия. None — без фильтрации.
            Кортеж типов — isinstance(action, action_class) с любым
            из перечисленных. Покрывает иерархию наследования:
            если указан BaseOrderAction, все наследники совпадут.

        action_name_pattern: regex по полному строковому имени действия.
            None — без фильтрации. Применяется через re.search
            (совпадение в любом месте строки). Компилируется один раз
            в __post_init__. Невалидный regex → ValueError.
            Примеры: r"orders\\..*", r".*Payment.*".

        aspect_name_pattern: regex по имени аспекта. None — без фильтрации.
            Применим ТОЛЬКО к наследникам AspectEvent (событиям с полем
            aspect_name). Для не-аспектных event_class — ValueError
            в __post_init__. Компилируется один раз.
            Примеры: r"validate_.*", r"process_payment".

        nest_level: фильтр по уровню вложенности. None — без фильтрации.
            int нормализуется в tuple[int] в __post_init__.
            Проверка: event.nest_level in nest_level.
            Примеры: (0,) — только корневые, (0, 1) — корневые и первый уровень.

        domain: фильтр по бизнес-домену действия. None — без фильтрации.
            Проверяется через GateCoordinator: ``get_snapshot(action_class, \"meta\").domain`` is domain.
            Пример: OrdersDomain.

        predicate: произвольная функция фильтрации. None — без фильтрации.
            Формальная аннотация: Callable[[BasePluginEvent], bool].
            Фактический тип event в рантайме гарантированно соответствует
            event_class, потому что predicate вызывается ПОСЛЕ проверки
            isinstance(event, event_class). Обращение к специфичным
            полям event_class в лямбде безопасно.
            Пример: lambda e: e.duration_ms > 1000.

        ignore_exceptions: подавление ошибок обработчика.
            True — ошибка обработчика подавляется, остальные плагины
            продолжают работу. По умолчанию True.
            False — ошибка пробрасывается наружу из emit_event(),
            прерывая выполнение.

        method_name: имя метода-обработчика в классе плагина.
            Записывается декоратором @on для диагностики и логирования.
            Пример: "on_slow_order_finish".
    """

    # ── Обязательные поля ──────────────────────────────────────────────
    event_class: type[BasePluginEvent]
    method_name: str

    # ── Фильтры (все опциональные, None = без фильтрации) ─────────────
    action_class: tuple[type, ...] | None = None
    action_name_pattern: str | None = None
    aspect_name_pattern: str | None = None
    nest_level: tuple[int, ...] | None = None
    domain: type | None = None
    predicate: Callable[[BasePluginEvent], bool] | None = None

    # ── Поведение при ошибке ───────────────────────────────────────────
    ignore_exceptions: bool = True

    # ── Валидация и кеширование ────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Выполняет валидацию и кеширование при создании экземпляра.

        Порядок:
        1. Проверка event_class — подкласс BasePluginEvent.
        2. Проверка aspect_name_pattern — применим только к AspectEvent.
        3. Нормализация nest_level: int → tuple[int].
        4. Компиляция action_name_pattern в re.Pattern.
        5. Компиляция aspect_name_pattern в re.Pattern.

        Компилированные паттерны записываются через object.__setattr__
        (обход frozen dataclass).

        Исключения:
            TypeError: event_class не подкласс BasePluginEvent.
            ValueError: aspect_name_pattern указан для не-аспектного event_class;
                        невалидный regex в action_name_pattern или
                        aspect_name_pattern.
        """
        # ── 1. Проверка event_class ──
        if not isinstance(self.event_class, type) or not issubclass(
            self.event_class, BasePluginEvent
        ):
            raise TypeError(
                f"SubscriptionInfo: event_class должен быть подклассом "
                f"BasePluginEvent, получен {self.event_class!r}."
            )

        # ── 2. Проверка aspect_name_pattern ──
        if self.aspect_name_pattern is not None:
            if not issubclass(self.event_class, AspectEvent):
                raise ValueError(
                    f"SubscriptionInfo: aspect_name_pattern указан, но "
                    f"event_class={self.event_class.__name__} не является "
                    f"подклассом AspectEvent. Фильтр aspect_name_pattern "
                    f"применим только к событиям аспектов (AspectEvent "
                    f"и наследники)."
                )

        # ── 3. Нормализация nest_level ──
        raw_nest = self.nest_level
        if isinstance(raw_nest, int):
            object.__setattr__(self, "nest_level", (raw_nest,))

        # ── 4. Компиляция action_name_pattern ──
        compiled_action: re.Pattern[str] | None = None
        if self.action_name_pattern is not None:
            try:
                compiled_action = re.compile(self.action_name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"SubscriptionInfo: невалидный regex в "
                    f"action_name_pattern: {self.action_name_pattern!r}. "
                    f"Ошибка: {exc}"
                ) from exc
        object.__setattr__(self, "_compiled_action_name_pattern", compiled_action)

        # ── 5. Компиляция aspect_name_pattern ──
        compiled_aspect: re.Pattern[str] | None = None
        if self.aspect_name_pattern is not None:
            try:
                compiled_aspect = re.compile(self.aspect_name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"SubscriptionInfo: невалидный regex в "
                    f"aspect_name_pattern: {self.aspect_name_pattern!r}. "
                    f"Ошибка: {exc}"
                ) from exc
        object.__setattr__(self, "_compiled_aspect_name_pattern", compiled_aspect)

    # ── Вычисляемые свойства ───────────────────────────────────────────

    @property
    def compiled_action_name_pattern(self) -> re.Pattern[str] | None:
        """
        Компилированный regex для action_name_pattern.

        Создаётся один раз в __post_init__ через object.__setattr__.
        None если action_name_pattern не указан.
        """
        return self._compiled_action_name_pattern  # type: ignore[attr-defined, no-any-return]

    @property
    def compiled_aspect_name_pattern(self) -> re.Pattern[str] | None:
        """
        Компилированный regex для aspect_name_pattern.

        Создаётся один раз в __post_init__ через object.__setattr__.
        None если aspect_name_pattern не указан.
        """
        return self._compiled_aspect_name_pattern  # type: ignore[attr-defined, no-any-return]

    # ── Методы проверки фильтров ───────────────────────────────────────

    def matches_event_class(self, event: BasePluginEvent) -> bool:
        """
        Проверяет совпадение типа события через isinstance.

        Шаг 1 в цепочке фильтров. Самая дешёвая проверка — одна
        инструкция isinstance. Отсекает ~90% подписок, потому что
        большинство плагинов подписаны на конкретные типы событий.

        Аргументы:
            event: объект события.

        Возвращает:
            True если событие является экземпляром event_class
            или его наследника.
        """
        return isinstance(event, self.event_class)

    def matches_action_class(self, action: Any) -> bool:
        """
        Проверяет совпадение типа действия через isinstance.

        Шаг 2 в цепочке фильтров. Дешёвая проверка — isinstance.
        Пропускается если action_class is None.

        Аргументы:
            action: экземпляр действия.

        Возвращает:
            True если action_class is None или action является
            экземпляром одного из классов в action_class.
        """
        if self.action_class is None:
            return True
        return isinstance(action, self.action_class)

    def matches_action_name(self, action_name: str) -> bool:
        """
        Проверяет совпадение строкового имени действия через regex.

        Шаг 3 в цепочке фильтров. Используется предкомпилированный
        паттерн _compiled_action_name_pattern. Применяется re.search
        (совпадение в любом месте строки, не fullmatch).

        Аргументы:
            action_name: полное строковое имя действия.

        Возвращает:
            True если action_name_pattern is None или regex совпал.
        """
        pattern = self._compiled_action_name_pattern  # type: ignore[attr-defined]
        if pattern is None:
            return True
        return pattern.search(action_name) is not None

    def matches_aspect_name(self, event: BasePluginEvent) -> bool:
        """
        Проверяет совпадение имени аспекта через regex.

        Шаг 4 в цепочке фильтров. Применяется только к событиям
        с полем aspect_name (наследникам AspectEvent). Для событий
        без aspect_name — всегда True (фильтр пропускается).

        Аргументы:
            event: объект события.

        Возвращает:
            True если aspect_name_pattern is None, или событие
            не является AspectEvent, или regex совпал с aspect_name.
        """
        pattern = self._compiled_aspect_name_pattern  # type: ignore[attr-defined]
        if pattern is None:
            return True
        if not isinstance(event, AspectEvent):
            return True
        return pattern.search(event.aspect_name) is not None

    def matches_nest_level(self, event_nest_level: int) -> bool:
        """
        Проверяет совпадение уровня вложенности.

        Шаг 5 в цепочке фильтров. Дешёвая проверка — оператор in
        для tuple[int]. Пропускается если nest_level is None.

        Аргументы:
            event_nest_level: уровень вложенности из события.

        Возвращает:
            True если nest_level is None или event_nest_level
            содержится в кортеже nest_level.
        """
        if self.nest_level is None:
            return True
        return event_nest_level in self.nest_level

    def matches_predicate(self, event: BasePluginEvent) -> bool:
        """
        Проверяет произвольный предикат.

        Шаг 7 (последний) в цепочке фильтров. Самая дорогая проверка —
        вызов произвольной пользовательской функции. К моменту вызова
        гарантировано: isinstance(event, event_class), поэтому обращение
        к специфичным полям event_class безопасно.

        Пропускается если predicate is None.

        Аргументы:
            event: объект события.

        Возвращает:
            True если predicate is None или predicate(event) вернул True.
        """
        if self.predicate is None:
            return True
        return self.predicate(event)
