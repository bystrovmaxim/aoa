# src/action_machine/core/base_action_machine.py
"""
Абстрактный базовый класс для всех машин действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseActionMachine определяет контракт для всех машин действий в системе.
Машина — центральный исполнитель, который принимает действие (Action),
входные параметры (Params), контекст (Context) и соединения (connections),
а затем выполняет конвейер аспектов с проверкой ролей, валидацией
и уведомлением плагинов.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ МАШИН
═══════════════════════════════════════════════════════════════════════════════

BaseActionMachine определяет два уровня API:

1. ПУБЛИЧНЫЙ: абстрактный метод ``run()`` — точка входа для внешнего кода.
   Конкретные реализации определяют, является ли run() асинхронным
   (ActionProductMachine) или синхронным (SyncActionProductMachine).

2. ВНУТРЕННИЙ: метод ``_run_internal()`` — реализация конвейера с поддержкой
   вложенности, ресурсов и параметра rollup. Вызывается из run()
   и рекурсивно из ToolsBox.run() для дочерних действий.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТР ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Параметр ``rollup: bool`` в ``_run_internal()`` управляет режимом
агрегации результатов. Production-машины (ActionProductMachine,
SyncActionProductMachine) всегда передают rollup=False. Тестовые машины
(AsyncTestMachine, SyncTestMachine) принимают rollup как обязательный
параметр без значения по умолчанию — тестировщик явно выбирает режим.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine          (async, production)
        │       │
        │       └── AsyncTestMachine      (async, тестовая, в пакете testing/)
        │
        └── SyncActionProductMachine      (sync, production)
                │
                └── SyncTestMachine       (sync, тестовая, в пакете testing/)

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. STATELESS МЕЖДУ ЗАПРОСАМИ: машина не хранит мутабельного состояния
   между вызовами run(). Каждый вызов полностью изолирован.

2. НЕ ПОДАВЛЯЕТ ИСКЛЮЧЕНИЯ: ошибки пробрасываются наружу с информативными
   сообщениями.

3. КОНТРАКТ _run_internal(): все конкретные машины реализуют _run_internal()
   с единой сигнатурой, включающей resources, connections, nested_level
   и rollup.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Абстрактный базовый класс для всех машин действий.

    Определяет контракт: публичный метод run() (абстрактный) и внутренний _run_internal().
    Конкретные реализации наследуют этот класс и определяют поведение
    run() (async или sync) и полную логику _run_internal().

    Машина не содержит мутабельного состояния между вызовами run().
    """

    @abstractmethod
    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Выполняет действие и возвращает результат.

        Это публичная точка входа. В асинхронных машинах (ActionProductMachine)
        это coroutine, вызываемый через await. В синхронных машинах
        (SyncActionProductMachine) это обычный метод.

        Аргументы:
            context: контекст выполнения (пользователь, запрос, окружение).
            action: экземпляр действия для выполнения.
            params: входные параметры действия.
            connections: словарь ресурсных менеджеров (соединений).
                         Ключ — строковое имя (совпадает с key в @connection).
                         Значение — экземпляр BaseResourceManager.
                         None если действие не объявляет @connection.

        Возвращает:
            Результат выполнения действия (тип R).
        """
        pass

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """
        Внутренний метод выполнения с поддержкой вложенности и rollup.

        Вызывается из run() (nested_level=0) и рекурсивно из ToolsBox.run()
        для дочерних действий (nested_level > 0).

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки в тестах, None в production).
            connections: словарь менеджеров ресурсов.
            nested_level: текущий уровень вложенности (0 — корневой).
            rollup: режим агрегации результатов. Production-машины
                    всегда передают False. Тестовые машины принимают
                    значение от тестировщика.

        Возвращает:
            R — результат выполнения действия.

        Исключения:
            NotImplementedError: если конкретная машина не переопределила метод.
        """
        raise NotImplementedError
