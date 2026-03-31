# examples/fastapi_service/actions/ping.py
"""
PingAction — действие проверки доступности сервиса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Минимальное действие без аутентификации. Возвращает ``{"message": "pong"}``.
Используется для проверки работоспособности сервиса, мониторинга
и smoke-тестов после деплоя.

═══════════════════════════════════════════════════════════════════════════════
ЭНДПОИНТ
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/ping → {"message": "pong"}

═══════════════════════════════════════════════════════════════════════════════
КОНФИГУРАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- @meta: описание "Проверка доступности сервиса", домен SystemDomain.
- @CheckRoles(NONE): доступно без аутентификации.
- Params: пустые (BaseParams).
- Result: PingResult с полем message.
"""

from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from ..domains import SystemDomain


class PingParams(BaseParams):
    """Параметры пинг-запроса. Пустые — действие не принимает входных данных."""
    pass


class PingResult(BaseResult):
    """Результат пинг-запроса."""
    message: str = Field(description="Ответное сообщение", examples=["pong"])


@meta(description="Проверка доступности сервиса", domain=SystemDomain)
@CheckRoles(CheckRoles.NONE, desc="Доступно без аутентификации")
class PingAction(BaseAction[PingParams, PingResult]):
    """
    Действие проверки доступности.

    Возвращает фиксированный ответ ``{"message": "pong"}``.
    Не требует аутентификации, не имеет зависимостей и соединений.
    """

    @summary_aspect("Формирование ответа pong")
    async def pong(
        self,
        params: PingParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> PingResult:
        """Формирует и возвращает ответ pong."""
        return PingResult(message="pong")
