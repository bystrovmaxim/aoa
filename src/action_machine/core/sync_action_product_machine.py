# src/action_machine/core/sync_action_product_machine.py
"""
SyncActionProductMachine — синхронная production-реализация машины действий.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

SyncActionProductMachine — синхронный аналог ActionProductMachine. Метод
run() является обычным (не async) methodом, который создаёт event loop
через asyncio.run() и выполняет асинхронный конвейер внутри него.

Предназначен для использования в синхронных окружениях:
- Скрипты командной строки (CLI).
- Celery-задачи (если не используется async worker).
- Django views без async-поддержки.
- Любой код, где нет активного event loop.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ ActionProductMachine
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine:
        async def run(...) → R              ← требует await
        Использование: await machine.run(ctx, action, params)

    SyncActionProductMachine:
        def run(...) → R                    ← обычный вызов
        Использование: result = machine.run(ctx, action, params)

Внутренняя реализация (_run_internal) полностью наследуется от
ActionProductMachine без изменений. SyncActionProductMachine только
переопределяет точку входа run(), оборачивая асинхронный _run_internal()
в asyncio.run().

═══════════════════════════════════════════════════════════════════════════════
ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Production-машина всегда передаёт rollup=False в _run_internal().
Параметр rollup не входит в публичный API production-машин.

Rollup доступен только через TestBench, который вызывает _run_internal()
напрямую с rollup из терминальных methodов (run, run_aspect, run_summary).

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Нельзя вызывать run() внутри уже работающего event loop. Если попытаться
вызвать из async-contextа (например, из FastAPI endpoint), asyncio.run()
выбросит RuntimeError. В таком случае используйте ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine          (async, production)
        │
        └── SyncActionProductMachine      (sync, production)  ← этот класс

SyncActionProductMachine наследует ActionProductMachine, получая всю
логику конвейера, проверки ролей, валидации соединений, checkerов,
плагинов и прокидывания rollup. Переопределяется только публичный
method run().

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.core.sync_action_product_machine import SyncActionProductMachine

    machine = SyncActionProductMachine(mode="production")

    # Синхронный вызов — без await:
    result = machine.run(context, action, params)

    # В CLI-скрипте:
    if __name__ == "__main__":
        ctx = Context()
        action = PingAction()
        params = PingAction.Params()
        result = machine.run(ctx, action, params)
        print(result.message)
"""

import asyncio
from typing import TypeVar

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class SyncActionProductMachine(ActionProductMachine):
    """
    Синхронная production-реализация машины действий.

    Наследует всю логику ActionProductMachine (конвейер аспектов,
    проверка ролей, валидация соединений, checkerы, плагины, прокидывание
    rollup). Переопределяет только публичный method run(), делая его
    синхронным.

    Внутри run() вызывается asyncio.run(), который создаёт новый
    event loop и выполняет асинхронный _run_internal().

    Всегда передаёт rollup=False — production-машина не поддерживает
    rollup через публичный API.

    Атрибуты наследуются от ActionProductMachine:
        _mode : str — режим выполнения.
        _plugin_coordinator : PluginCoordinator — координатор плагинов.
        _log_coordinator : LogCoordinator — координатор логирования.
    """

    def run(  # type: ignore[override]  # pylint: disable=invalid-overridden-method
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Синхронно выполняет действие.

        Создаёт новый event loop через asyncio.run() и выполняет
        асинхронный _run_internal() внутри него. Production-машина
        всегда передаёт rollup=False.

        Args:
            context: context выполнения (пользователь, запрос, окружение).
            action: экземпляр действия для выполнения.
            params: входные параметры действия.
            connections: словарь ресурсных менеджеров (или None).

        Returns:
            R — результат выполнения действия.

        Raises:
            RuntimeError: если вызван внутри уже работающего event loop.
                          В async-contextе используйте ActionProductMachine.
            AuthorizationError: при несоответствии ролей.
            ConnectionValidationError: при несоответствии соединений.
            ValidationFieldError: при ошибке валидации checkerом.
            TypeError: при отсутствии @check_roles или ошибке типов.
        """
        return asyncio.run(
            self._run_internal(
                context=context,
                action=action,
                params=params,
                resources=None,
                connections=connections,
                nested_level=0,
                rollup=False,
            )
        )
