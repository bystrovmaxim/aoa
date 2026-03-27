# src/action_machine/core/action_test_machine.py
"""
Модуль: ActionTestMachine — тестовая машина действий с поддержкой моков.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionTestMachine наследует ActionProductMachine и добавляет возможность
подстановки зависимостей через словарь моков. Это позволяет тестировать
действия изолированно, заменяя реальные сервисы (PaymentService,
NotificationService и т.д.) на моки.

═══════════════════════════════════════════════════════════════════════════════
STATELESS МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Как и родительская машина, ActionTestMachine не хранит состояния между
вызовами run(), связанного с зависимостями. Фабрики зависимостей хранятся
в координаторе (GateCoordinator) и являются stateless.

Моки — это не состояние машины в смысле кеширования. Это конфигурация,
заданная при создании машины и неизменяемая после этого. Моки передаются
как resources в _run_internal и имеют приоритет над фабрикой при resolve().

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С GATECOORDINATOR
═══════════════════════════════════════════════════════════════════════════════

Тестовая машина использует тот же GateCoordinator, что и родительская
ActionProductMachine. Координатор передаётся через конструктор (DI).
Если не указан — создаётся по умолчанию в родителе.

Метод build_factory() делегирует координатору создание DependencyFactory
для класса действия, что позволяет тестировать отдельные аспекты
без запуска всей машины.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП РАБОТЫ МОКОВ
═══════════════════════════════════════════════════════════════════════════════

Моки передаются как словарь {класс_зависимости: mock_значение}.
Тестовая машина подготавливает моки один раз в конструкторе (_prepare_mock)
и затем передаёт их как resources в _run_internal родителя.

ToolsBox при вызове box.resolve(PaymentService) сначала ищет в resources
(т.е. в моках), и только потом обращается к фабрике. Поэтому моки имеют
приоритет над реальными зависимостями.

Поддерживаемые типы mock-значений:
- MockAction         → используется как есть (прямой вызов .run()).
- BaseAction         → выполняется через конвейер аспектов.
- BaseResult         → оборачивается в MockAction(result=...).
- callable           → оборачивается в MockAction(side_effect=...).
- любой другой объект → возвращается как есть через resolve().

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.core.action_test_machine import ActionTestMachine

    # Создаём моки зависимостей
    mock_payment = PaymentService(gateway="test")
    mock_notifier = NotificationService()

    # Создаём тестовую машину
    machine = ActionTestMachine(
        mocks={
            PaymentService: mock_payment,
            NotificationService: mock_notifier,
        },
    )

    # Выполняем действие — зависимости будут взяты из моков
    result = await machine.run(
        context=test_context,
        action=CreateOrderAction(),
        params=OrderParams(user_id="test", amount=100.0),
    )

    # Проверяем, что мок был вызван
    assert len(mock_payment.processed) == 1

    # Тестирование отдельного аспекта вне машины:
    factory = machine.build_factory(CreateOrderAction)
    box = ToolsBox(factory=factory, resources=machine._prepared_mocks, ...)
    payment = box.resolve(PaymentService)  # вернёт mock_payment
"""

from typing import Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.mock_action import MockAction
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина действий с удобным API для подстановки зависимостей.

    Полностью асинхронная (как родитель). Принимает словарь моков
    в конструкторе и передаёт их как resources при выполнении,
    что даёт мокам приоритет над фабрикой зависимостей.

    Для MockAction выполнение идёт напрямую через .run() (без конвейера
    аспектов, без проверки ролей и соединений).

    Машина не хранит состояния между вызовами run(), связанного
    с зависимостями. Фабрики хранятся в координаторе. Моки —
    это неизменяемая конфигурация, заданная при создании.

    Атрибуты:
        _mocks : dict[type, Any]
            Исходный словарь моков, переданный в конструктор.
        _prepared_mocks : dict[type, Any]
            Подготовленные моки (MockAction, BaseAction или объекты).
    """

    def __init__(
        self,
        mocks: dict[type[Any], Any] | None = None,
        mode: str = "test",
        coordinator: GateCoordinator | None = None,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует тестовую машину.

        Аргументы:
            mocks: словарь подстановок {класс_зависимости: mock_значение}.
                   Ключ — класс зависимости (тот же, что в @depends).
                   Значение — мок (см. _prepare_mock).
            mode: режим выполнения (по умолчанию "test"). Передаётся родителю.
            coordinator: координатор метаданных и фабрик. Если не указан,
                         родитель создаст новый экземпляр GateCoordinator().
                         Координатор — единственный владелец метаданных
                         и фабрик.
            log_coordinator: координатор логирования. Если не указан, родитель
                             создаст координатор с ConsoleLogger по умолчанию.
        """
        super().__init__(
            mode=mode,
            coordinator=coordinator,
            log_coordinator=log_coordinator,
        )

        self._mocks: dict[type[Any], Any] = mocks or {}
        self._prepared_mocks: dict[type[Any], Any] = {}

        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    # ─────────────────────────────────────────────────────────────────────
    # Подготовка моков
    # ─────────────────────────────────────────────────────────────────────

    def _prepare_mock(self, value: Any) -> Any:
        """
        Преобразует переданное значение в объект, пригодный для использования.

        Правила преобразования:
        - MockAction   → используется как есть.
        - BaseAction   → используется как есть (будет выполнен через конвейер).
        - callable     → оборачивается в MockAction(side_effect=value).
        - BaseResult   → оборачивается в MockAction(result=value).
        - любой другой → используется как есть (для resolve()).

        Аргументы:
            value: mock-значение из словаря.

        Возвращает:
            Подготовленный объект.
        """
        if isinstance(value, MockAction):
            return value
        if isinstance(value, BaseAction):
            return value
        if callable(value):
            return MockAction(side_effect=value)
        if isinstance(value, BaseResult):
            return MockAction(result=value)
        return value

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API: run
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Выполняет действие с поддержкой моков.

        Для MockAction — прямой вызов action.run(params) без конвейера.
        Для обычных действий — вызов _run_internal с моками как resources,
        что даёт им приоритет при resolve() в ToolsBox.

        Каждый вызов полностью изолирован от предыдущих.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            R — результат выполнения действия.
        """
        if isinstance(action, MockAction):
            return cast(R, action.run(params))

        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=self._prepared_mocks,
            connections=connections,
            nested_level=0,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Внутренний метод выполнения (переопределение)
    # ─────────────────────────────────────────────────────────────────────

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> R:
        """
        Внутренний метод выполнения с поддержкой моков.

        Для MockAction — прямой вызов без конвейера.
        Для обычных действий — делегирование родительскому _run_internal,
        который получает метаданные и фабрику через координатор и выполняет
        полный конвейер с проверками.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки). Передаются в ToolsBox,
                       где имеют приоритет над фабрикой при resolve().
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности.

        Возвращает:
            R — результат действия.
        """
        if isinstance(action, MockAction):
            return cast(R, action.run(params))

        return await super()._run_internal(
            context=context,
            action=action,
            params=params,
            resources=resources,
            connections=connections,
            nested_level=nested_level,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Утилиты для тестирования
    # ─────────────────────────────────────────────────────────────────────

    def build_factory(
        self, action_class: type[BaseAction[Any, Any]],
    ) -> DependencyFactory:
        """
        Возвращает DependencyFactory для класса действия через координатор.

        Полезно для тестирования отдельных аспектов вне машины:
        можно получить фабрику, создать ToolsBox и вызвать метод-аспект
        напрямую.

        Делегирует координатору (self._coordinator.get_factory), который
        лениво создаёт и кеширует stateless-фабрику для класса.

        Аргументы:
            action_class: класс действия (не экземпляр).

        Возвращает:
            DependencyFactory — stateless-фабрика зависимостей для класса.

        Пример:
            machine = ActionTestMachine(mocks={PaymentService: mock_payment})
            factory = machine.build_factory(CreateOrderAction)
            box = ToolsBox(factory=factory, resources=machine._prepared_mocks, ...)
            payment = box.resolve(PaymentService)  # вернёт mock_payment
        """
        return self._coordinator.get_factory(action_class)
