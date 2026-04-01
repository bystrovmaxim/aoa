# tests/domain/ping_action.py
"""
PingAction — минимальное действие для smoke-тестов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Самое простое действие в тестовой доменной модели. Не принимает
параметров, не имеет зависимостей и connections, содержит только
summary-аспект, возвращающий фиксированное сообщение "pong".

Доступно всем пользователям (ROLE_NONE), включая анонимных.
Принадлежит SystemDomain.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

- Smoke-тесты: проверка базовой инфраструктуры (машина запускается,
  координатор собирает метаданные, конвейер выполняется).
- Тесты ROLE_NONE: анонимный пользователь без ролей проходит проверку.
- Тесты TestBench: минимальный прогон без моков и connections.

    result = await bench.run(PingAction(), PingAction.Params(), rollup=False)
    assert result.message == "pong"
"""

from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import SystemDomain


@meta(description="Проверка доступности сервиса", domain=SystemDomain)
@check_roles(ROLE_NONE)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):
    """
    Минимальное действие без параметров и зависимостей.

    Только summary-аспект, возвращающий фиксированный результат "pong".
    Доступно всем пользователям (ROLE_NONE).
    """

    class Params(BaseParams):
        """Параметры PingAction — пустые, действие не требует входных данных."""
        pass

    class Result(BaseResult):
        """Результат PingAction — сообщение pong."""
        message: str = Field(description="Ответное сообщение сервиса")

    @summary_aspect("Формирование ответа pong")
    async def pong(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "PingAction.Result":
        """Возвращает фиксированный результат с сообщением 'pong'."""
        return PingAction.Result(message="pong")
