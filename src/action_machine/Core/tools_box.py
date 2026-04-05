# src/action_machine/core/tools_box.py
"""
ToolsBox — frozen-контейнер инструментов для аспектов действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ToolsBox — единый объект, передаваемый в каждый аспект действия как
параметр box. Обеспечивает аспектам доступ ко всем инструментам:

- Получение зависимостей через resolve(cls, *args, **kwargs).
- Запуск дочерних действий через run(action_class, params, connections).
- Логирование через info/warning/error/debug.

═══════════════════════════════════════════════════════════════════════════════
ПРИВАТНОСТЬ КОНТЕКСТА — КЛЮЧЕВОЙ ИНВАРИАНТ
═══════════════════════════════════════════════════════════════════════════════

ToolsBox НЕ предоставляет доступа к контексту выполнения (Context).
Публичного свойства ``context`` нет. Публичного метода, возвращающего
Context, нет. Ни один публичный атрибут или метод не раскрывает Context.

Контекст хранится в приватном атрибуте через name mangling
(``self.__context``). Он используется ТОЛЬКО внутри ToolsBox:

- Передача в замыкание ``run_child`` для дочерних действий.
- Передача в ``ScopedLogger`` для шаблонов ``{%context.user.id}``.
- Передача в машину при создании ``aspect_box`` в ``_call_aspect``.

Единственный легальный путь к данным контекста для аспекта —
через ``ContextView``, который машина (ActionProductMachine) создаёт
для методов с декоратором ``@context_requires`` и передаёт как
параметр ``ctx``. ContextView содержит только те поля, которые аспект
явно запросил. Обращение к незапрошенному полю → ContextAccessError.

Это реализация принципа минимальных привилегий: аспект «Расчёт суммы»
не должен видеть ``user.roles``, если он их не запрашивал.

    ПРЕДУПРЕЖДЕНИЕ: Доступ через ``box._ToolsBox__context`` является
    нарушением контракта фреймворка. Name mangling — конвенция Python,
    а не security boundary. Фреймворк не может предотвратить намеренный
    обход, но гарантирует, что случайный доступ невозможен — нет
    публичного API, раскрывающего Context.

═══════════════════════════════════════════════════════════════════════════════
СВЯЗЬ С FROZEN CORE-ТИПАМИ
═══════════════════════════════════════════════════════════════════════════════

Приватность контекста и frozen-семантика State/Result — два аспекта
одной идеи: аспект работает в песочнице.

- Frozen State: аспект не может записать данные мимо чекеров.
- Приватный Context: аспект не может прочитать данные мимо ContextView.

Вместе они обеспечивают: аспект видит ровно то, что объявил через
@context_requires, и пишет ровно то, что проверено чекерами.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

ToolsBox хранит флаг rollup и прокидывает его на все уровни:

1. RESOLVE: при вызове ``box.resolve(cls)`` параметр rollup передаётся
   в ``factory.resolve(cls, rollup=self.__rollup)``. Если зависимость
   является BaseResourceManager и не поддерживает rollup —
   RollupNotSupportedError.

2. RUN (дочерние действия): при вызове ``box.run(ChildAction, params)``
   замыкание run_child передаёт rollup в machine._run_internal().
   Дочерняя машина создаёт новый ToolsBox с тем же rollup.

3. CONNECTIONS: обёртки (WrapperConnectionManager) наследуют rollup
   от оригинального менеджера через конструктор.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal(...)
        │
        │  Создаёт ToolsBox с:
        │  - run_child: замыкание для запуска дочерних действий
        │  - factory: DependencyFactory для текущего действия
        │  - resources: внешние ресурсы (моки в тестах)
        │  - context: Context (ПРИВАТНЫЙ, без публичного доступа)
        │  - log: ScopedLogger с координатами аспекта
        │  - nested_level: уровень вложенности
        │  - rollup: флаг автоотката транзакций
        ▼
    ToolsBox
        │
        ├── resolve(cls, *args, **kwargs) → ищет в resources, затем в factory
        ├── run(action, params)           → создаёт экземпляр, оборачивает connections
        ├── info(msg)                     → делегирует в ScopedLogger
        ├── warning(msg)                  → делегирует в ScopedLogger
        ├── error(msg)                    → делегирует в ScopedLogger
        └── debug(msg)                    → делегирует в ScopedLogger

    Аспект НЕ может получить Context через box.
    Только через ctx: ContextView при наличии @context_requires.

═══════════════════════════════════════════════════════════════════════════════
РЕЗОЛВ ЗАВИСИМОСТЕЙ
═══════════════════════════════════════════════════════════════════════════════

Метод resolve(cls, *args, **kwargs) реализует двухуровневый поиск:

1. Сначала проверяет resources — словарь внешних ресурсов. В production
   он обычно None. В тестах (TestBench) содержит моки, которые
   имеют приоритет над фабрикой.

2. Если в resources не найдено — делегирует в factory.resolve(cls, *args,
   rollup=self.__rollup, **kwargs), который создаёт новый экземпляр
   через фабрику или конструктор.

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК ДОЧЕРНИХ ДЕЙСТВИЙ
═══════════════════════════════════════════════════════════════════════════════

Метод run(action_class, params, connections) позволяет аспекту запустить
другое действие в рамках того же контекста. Connections оборачиваются
через get_wrapper_class(), чтобы дочернее действие не могло управлять
транзакциями родительского ресурса.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Обработка платежа")
    async def process_payment_aspect(self, params, state, box, connections):
        # Получение зависимости
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)

        # Логирование
        await box.info("Платёж обработан", txn_id=txn_id)

        # Запуск дочернего действия
        notify_result = await box.run(
            NotifyAction, NotifyParams(user_id=params.user_id, message="OK")
        )

        return {"txn_id": txn_id}

    # Доступ к контексту — ТОЛЬКО через @context_requires:
    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)  # ← единственный путь к контексту
        return {}

    # Попытка получить контекст через box — невозможна:
    # box.context          → AttributeError (свойства нет)
    # box["context"]       → KeyError (ключа нет)
    # box.get("context")   → None (атрибута нет)
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ToolsBox:
    """
    Frozen-контейнер инструментов для аспектов.

    Предоставляет методы для работы с зависимостями, логированием и запуском
    дочерних действий. Создаётся один раз на уровень вложенности и передаётся
    во все аспекты вместо отдельных параметров deps и log.

    НЕ предоставляет доступа к контексту выполнения (Context). Публичного
    свойства ``context`` нет. Публичного метода, возвращающего Context, нет.
    Контекст хранится в приватном атрибуте через name mangling и используется
    только внутри ToolsBox для передачи в run_child, ScopedLogger и машину.

    Аспекты получают данные контекста через ContextView, создаваемый
    машиной при наличии @context_requires.

    Публичные свойства (только чтение):
        run_child    — замыкание для запуска дочерних действий.
        factory      — stateless-фабрика зависимостей.
        resources    — внешние ресурсы (моки в тестах).
        nested_level — уровень вложенности вызова.
        rollup       — флаг автоотката транзакций.
    """

    __slots__ = (
        "__context",
        "__factory",
        "__log",
        "__nested_level",
        "__resources",
        "__rollup",
        "__run_child",
    )

    def __init__(
        self,
        run_child: Callable[..., Awaitable[BaseResult]],
        factory: DependencyFactory,
        resources: dict[type[Any], Any] | None,
        context: Context,
        log: ScopedLogger,
        nested_level: int,
        rollup: bool = False,
    ) -> None:
        """
        Инициализирует ToolsBox.

        Аргументы:
            run_child: функция для запуска дочернего действия (замыкание,
                       предоставляемое машиной).
            factory: stateless-фабрика зависимостей для текущего действия.
            resources: словарь внешних ресурсов. В production обычно None.
                       В тестах — моки.
            context: контекст выполнения текущего запроса. Хранится
                     в приватном атрибуте через name mangling. НЕ доступен
                     извне — аспекты получают данные контекста через
                     ContextView при наличии @context_requires.
            log: ScopedLogger, привязанный к текущему аспекту.
            nested_level: уровень вложенности вызова.
            rollup: флаг автоотката транзакций. По умолчанию False.
        """
        # Name mangling: self.__run_child → self._ToolsBox__run_child
        # Все атрибуты приватные. Публичный доступ — только через @property.
        object.__setattr__(self, "_ToolsBox__run_child", run_child)
        object.__setattr__(self, "_ToolsBox__factory", factory)
        object.__setattr__(self, "_ToolsBox__resources", resources)
        object.__setattr__(self, "_ToolsBox__context", context)
        object.__setattr__(self, "_ToolsBox__log", log)
        object.__setattr__(self, "_ToolsBox__nested_level", nested_level)
        object.__setattr__(self, "_ToolsBox__rollup", rollup)

    # ─────────────────────────────────────────────────────────────────────
    # Защита от записи
    # ─────────────────────────────────────────────────────────────────────

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Запрещает запись атрибутов. ToolsBox неизменяем после создания.

        Исключения:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"ToolsBox является frozen-объектом. "
            f"Запись атрибута '{name}' запрещена."
        )

    def __delattr__(self, name: str) -> None:
        """
        Запрещает удаление атрибутов. ToolsBox неизменяем после создания.

        Исключения:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"ToolsBox является frozen-объектом. "
            f"Удаление атрибута '{name}' запрещено."
        )

    # ─────────────────────────────────────────────────────────────────────
    # Публичные свойства (только чтение, без context)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def run_child(self) -> Callable[..., Awaitable[BaseResult]]:
        """Возвращает функцию запуска дочернего действия."""
        return self.__run_child  # type: ignore[has-type]

    @property
    def factory(self) -> DependencyFactory:
        """Возвращает stateless-фабрику зависимостей."""
        return self.__factory  # type: ignore[has-type]

    @property
    def resources(self) -> dict[type[Any], Any] | None:
        """Возвращает словарь внешних ресурсов."""
        return self.__resources  # type: ignore[has-type]

    @property
    def nested_level(self) -> int:
        """Возвращает уровень вложенности."""
        return self.__nested_level  # type: ignore[has-type]

    @property
    def rollup(self) -> bool:
        """Возвращает флаг автоотката транзакций."""
        return self.__rollup  # type: ignore[has-type]

    # ─────────────────────────────────────────────────────────────────────
    # Резолв зависимостей
    # ─────────────────────────────────────────────────────────────────────

    def resolve(self, cls: type[Any], *args: Any, **kwargs: Any) -> Any:
        """
        Возвращает экземпляр зависимости указанного класса.

        Двухуровневый поиск:
        1. Сначала ищет в resources (внешние ресурсы / моки).
        2. Если не найдено — делегирует в factory.resolve().

        Аргументы:
            cls: класс зависимости.
            *args: позиционные аргументы для фабрики или конструктора.
            **kwargs: именованные аргументы для фабрики или конструктора.

        Возвращает:
            Экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не найдена.
            RollupNotSupportedError: если rollup=True и зависимость
                не поддерживает rollup.
        """
        if self.__resources and cls in self.__resources:  # type: ignore[has-type]
            return self.__resources[cls]  # type: ignore[index]
        return self.__factory.resolve(cls, *args, rollup=self.__rollup, **kwargs)  # type: ignore[has-type]

    # ─────────────────────────────────────────────────────────────────────
    # Запуск дочерних действий
    # ─────────────────────────────────────────────────────────────────────

    def _wrap_connections(
        self, connections: dict[str, BaseResourceManager] | None,
    ) -> dict[str, BaseResourceManager] | None:
        """
        Обёртывает каждый ресурс в его класс-обёртку для передачи в дочерние действия.

        Обёртка запрещает дочернему действию управлять транзакциями
        (open/commit/rollback), но разрешает выполнять запросы (execute).

        Аргументы:
            connections: исходный словарь ресурсных менеджеров.

        Возвращает:
            Новый словарь с обёрнутыми ресурсами, или None если connections=None.
        """
        if connections is None:
            return None
        wrapped: dict[str, BaseResourceManager] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)  # type: ignore[call-arg]
            else:
                wrapped[key] = connection
        return wrapped

    async def run(
        self,
        action_class: type[BaseAction[P, R]],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Запускает дочернее действие с текущими ресурсами и контекстом.

        Создаёт экземпляр действия, обёртывает connections (если переданы),
        и вызывает замыкание run_child, которое делегирует в
        ActionProductMachine._run_internal() с увеличенным nested_level
        и текущим rollup.

        Аргументы:
            action_class: класс дочернего действия.
            params: параметры для дочернего действия.
            connections: словарь ресурсных менеджеров (опционально).

        Возвращает:
            Результат выполнения дочернего действия.
        """
        action_instance = action_class()
        wrapped_connections = self._wrap_connections(connections)

        result = await self.__run_child(  # type: ignore[has-type]
            action=action_instance,
            params=params,
            connections=wrapped_connections,
        )
        return cast("R", result)

    # ─────────────────────────────────────────────────────────────────────
    # Методы логирования (прокси к ScopedLogger)
    # ─────────────────────────────────────────────────────────────────────

    async def info(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня INFO.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.info(message, **kwargs)  # type: ignore[has-type]

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.warning(message, **kwargs)  # type: ignore[has-type]

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.error(message, **kwargs)  # type: ignore[has-type]

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.debug(message, **kwargs)  # type: ignore[has-type]
