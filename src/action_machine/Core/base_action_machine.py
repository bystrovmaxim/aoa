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
2. ВНУТРЕННИЙ: метод ``_run_internal()`` — реализация конвейера с поддержкой
   вложенности, ресурсов и параметра rollup.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТР ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Параметр ``rollup: bool`` в ``_run_internal()`` управляет режимом
агрегации результатов. Production-машины всегда передают rollup=False.
TestBench принимает rollup как обязательный параметр.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine          (async, production)
        │
        └── SyncActionProductMachine      (sync, production)
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
    Конкретные реализации наследуют этот класс и определяют поведение.
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

        Аргументы:
            context: контекст выполнения (пользователь, запрос, окружение).
            action: экземпляр действия для выполнения.
            params: входные параметры действия.
            connections: словарь ресурсных менеджеров (соединений).

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

        Вызывается из run() (nested_level=0) и рекурсивно из ToolsBox.run().
        """
        raise NotImplementedError