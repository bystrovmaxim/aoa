# src/action_machine/core/tools_box.py
"""
ToolsBox — контейнер инструментов для аспектов действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ToolsBox — единый объект, передаваемый в каждый аспект действия как
параметр box. Обеспечивает аспектам доступ ко всем инструментам:

- Получение зависимостей через resolve(cls, *args, **kwargs).
- Запуск дочерних действий через run(action_class, params, connections).
- Логирование через info/warning/error/debug.

ToolsBox заменяет ранее существовавшие отдельные параметры deps и log
единым интерфейсом. Создаётся ActionProductMachine один раз на уровень
вложенности и передаётся во все аспекты этого уровня.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

ToolsBox хранит флаг rollup и прокидывает его на все уровни:

1. RESOLVE: при вызове box.resolve(cls) параметр rollup передаётся
   в factory.resolve(cls, rollup=self._rollup). Если зависимость является
   BaseResourceManager и не поддерживает rollup — RollupNotSupportedError.

2. RUN (дочерние действия): при вызове box.run(ChildAction, params, connections)
   замыкание run_child передаёт rollup в machine._run_internal().
   Дочерняя машина создаёт новый ToolsBox с тем же rollup.

3. CONNECTIONS: обёртки (WrapperConnectionManager) наследуют rollup
   от оригинального менеджера через конструктор.

Цепочка прокидывания rollup:

    ActionProductMachine._run_internal(rollup=True)
        │
        └── ToolsBox(rollup=True)
                │
                ├── resolve(PaymentService)
                │       → factory.resolve(PaymentService, rollup=True)
                │       → check_rollup_support() если BaseResourceManager
                │
                └── run(ChildAction, params, connections)
                        │
                        └── machine._run_internal(rollup=True)
                                │
                                └── ToolsBox(rollup=True)
                                        └── ... (рекурсивно)

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal(...)
        │
        │  Создаёт ToolsBox с:
        │  - run_child: замыкание для запуска дочерних действий
        │  - factory: DependencyFactory для текущего действия
        │  - resources: внешние ресурсы (моки в тестах)
        │  - context: Context текущего запроса
        │  - log: ScopedLogger с координатами аспекта
        │  - nested_level: уровень вложенности
        │  - rollup: флаг автоотката транзакций
        ▼
    ToolsBox
        │
        ├── resolve(cls, *args, **kwargs) → ищет в resources, затем в factory (с rollup)
        ├── run(action, p)               → создаёт экземпляр, оборачивает connections, вызывает run_child
        ├── info(msg)                    → делегирует в ScopedLogger → LogCoordinator
        ├── warning(msg)                 → делегирует в ScopedLogger → LogCoordinator
        ├── error(msg)                   → делегирует в ScopedLogger → LogCoordinator
        └── debug(msg)                   → делегирует в ScopedLogger → LogCoordinator

═══════════════════════════════════════════════════════════════════════════════
РЕЗОЛВ ЗАВИСИМОСТЕЙ
═══════════════════════════════════════════════════════════════════════════════

Метод resolve(cls, *args, **kwargs) реализует двухуровневый поиск:

1. Сначала проверяет resources — словарь внешних ресурсов. В production
   он обычно None. В тестах (TestBench) содержит моки, которые
   имеют приоритет над фабрикой.

2. Если в resources не найдено — делегирует в factory.resolve(cls, *args,
   rollup=self._rollup, **kwargs), который создаёт новый экземпляр
   через фабрику или конструктор. При rollup=True фабрика дополнительно
   проверяет поддержку rollup для BaseResourceManager.

Аргументы *args и **kwargs пробрасываются в factory.resolve(), что
позволяет аспектам передавать рантайм-параметры при создании зависимостей.

═══════════════════════════════════════════════════════════════════════════════
ЗАПУСК ДОЧЕРНИХ ДЕЙСТВИЙ
═══════════════════════════════════════════════════════════════════════════════

Метод run(action_class, params, connections) позволяет аспекту запустить
другое действие в рамках того же контекста. Connections оборачиваются
через get_wrapper_class(), чтобы дочернее действие не могло управлять
транзакциями родительского ресурса. Rollup прокидывается через замыкание
run_child в machine._run_internal().

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Обработка платежа")
    async def process_payment(self, params, state, box, connections):
        # Получение зависимости (rollup прокидывается автоматически)
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)

        # Получение зависимости с рантайм-параметрами
        logger = box.resolve(AuditLogger, level="verbose")

        # Логирование
        await box.info("Платёж обработан", txn_id=txn_id)

        # Запуск дочернего действия (rollup прокидывается через run_child)
        notify_result = await box.run(
            NotifyAction, NotifyParams(user_id=params.user_id, message="OK")
        )

        return {"txn_id": txn_id}
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
    Контейнер инструментов для аспектов.

    Предоставляет методы для работы с зависимостями, логированием и запуском
    дочерних действий. Создаётся один раз на уровень вложенности и передаётся
    во все аспекты вместо отдельных параметров deps и log.

    Хранит флаг rollup и прокидывает его в resolve() и run().

    Атрибуты (доступны через свойства):
        run_child : Callable — замыкание для запуска дочерних действий.
        factory : DependencyFactory — stateless-фабрика зависимостей текущего действия.
        resources : dict[type, Any] | None — внешние ресурсы (моки в тестах).
        context : Context — контекст выполнения текущего запроса.
        nested_level : int — уровень вложенности вызова.
        rollup : bool — флаг автоотката транзакций.
    """

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
                       предоставляемое машиной). Принимает action, params,
                       connections и возвращает BaseResult. Замыкание
                       захватывает rollup из машины.
            factory: stateless-фабрика зависимостей для текущего действия.
                     Каждый вызов factory.resolve() создаёт новый экземпляр.
            resources: словарь внешних ресурсов, переданных на этот уровень.
                       В production обычно None. В тестах — моки.
                       При наличии ресурса в этом словаре он имеет приоритет
                       над фабрикой.
            context: контекст выполнения текущего запроса.
            log: ScopedLogger, привязанный к текущему аспекту.
            nested_level: уровень вложенности вызова.
            rollup: флаг автоотката транзакций. При True:
                    - resolve() передаёт rollup=True в factory.resolve().
                    - run() прокидывает rollup через замыкание run_child.
                    По умолчанию False.
        """
        self.__run_child = run_child
        self.__factory = factory
        self.__resources = resources
        self.__context = context
        self.__log = log
        self.__nested_level = nested_level
        self.__rollup = rollup

    @property
    def run_child(self) -> Callable[..., Awaitable[BaseResult]]:
        """Возвращает функцию запуска дочернего действия."""
        return self.__run_child

    @property
    def factory(self) -> DependencyFactory:
        """Возвращает stateless-фабрику зависимостей."""
        return self.__factory

    @property
    def resources(self) -> dict[type[Any], Any] | None:
        """Возвращает словарь внешних ресурсов."""
        return self.__resources

    @property
    def context(self) -> Context:
        """Возвращает контекст выполнения."""
        return self.__context

    @property
    def nested_level(self) -> int:
        """Возвращает уровень вложенности."""
        return self.__nested_level

    @property
    def rollup(self) -> bool:
        """Возвращает флаг автоотката транзакций."""
        return self.__rollup

    def resolve(self, cls: type[Any], *args: Any, **kwargs: Any) -> Any:
        """
        Возвращает экземпляр зависимости указанного класса.

        Двухуровневый поиск:
        1. Сначала ищет в resources (внешние ресурсы / моки).
           Если найдено — возвращает объект из resources.
           Аргументы *args и **kwargs игнорируются при возврате из resources,
           так как объект уже создан.
        2. Если не найдено — делегирует в factory.resolve(cls, *args,
           rollup=self.__rollup, **kwargs), который создаёт новый экземпляр
           через фабрику или конструктор. При rollup=True фабрика
           дополнительно проверяет check_rollup_support() для
           BaseResourceManager.

        Аргументы:
            cls: класс зависимости.
            *args: позиционные аргументы для фабрики или конструктора.
            **kwargs: именованные аргументы для фабрики или конструктора.

        Возвращает:
            Экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не найдена ни в ресурсах, ни в фабрике.
            RollupNotSupportedError: если rollup=True и зависимость —
                BaseResourceManager без поддержки rollup.
        """
        if self.__resources and cls in self.__resources:
            return self.__resources[cls]
        return self.__factory.resolve(cls, *args, rollup=self.__rollup, **kwargs)

    def _wrap_connections(
        self, connections: dict[str, BaseResourceManager] | None
    ) -> dict[str, BaseResourceManager] | None:
        """
        Обёртывает каждый ресурс в его класс-обёртку для передачи в дочерние действия.

        Обёртка запрещает дочернему действию управлять транзакциями
        (open/commit/rollback), но разрешает выполнять запросы (execute).
        Если get_wrapper_class() возвращает None, ресурс передаётся как есть.

        Флаг rollup прокидывается через обёртку: WrapperConnectionManager
        наследует rollup из оригинального менеджера в своём конструкторе.

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

        result = await self.__run_child(
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
        await self.__log.info(message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.warning(message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.error(message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Аргументы:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.debug(message, **kwargs)
