# src/examples/fastapi_mcp_services/actions/ping.py
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
ПАТТЕРН ВЛОЖЕННЫХ МОДЕЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Params и Result определяются как вложенные классы внутри Action:

    class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):
        class Params(BaseParams): ...
        class Result(BaseResult): ...

Преимущества:

1. ЛОКАЛЬНОСТЬ — модели данных находятся рядом с логикой, которая их
   использует. Не нужно искать определение в другом месте файла.

2. ПРОСТРАНСТВО ИМЁН — ``PingAction.Params`` и ``CreateOrderAction.Params``
   не конфликтуют. Каждое действие владеет своими моделями.

3. САМОДОКУМЕНТИРОВАНИЕ — открыв класс действия, разработчик видит
   полную картину: входные данные, выходные данные, логику обработки.

Generic-параметры указываются как строковые forward references
(``"PingAction.Params"``), потому что вложенные классы ещё не существуют
на момент определения наследования. Функция ``extract_action_types``
резолвит ForwardRef через модуль и пространство имён класса.

Описание действия берётся из ``@meta(description=...)``, описания
аспектов — из ``@summary_aspect("...")``. Отдельный docstring на классе
действия не нужен — это дублирование.

═══════════════════════════════════════════════════════════════════════════════
КОНФИГУРАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- @meta: описание "Проверка доступности сервиса", домен SystemDomain.
- @CheckRoles(NONE): доступно без аутентификации.
- Params: пустые (BaseParams без полей).
- Result: поле message.
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


@meta(description="Проверка доступности сервиса", domain=SystemDomain)
@CheckRoles(CheckRoles.NONE)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):

    class Params(BaseParams):
        """Параметры пинг-запроса. Пустые — действие не принимает входных данных."""
        pass

    class Result(BaseResult):
        """Результат пинг-запроса."""
        message: str = Field(description="Ответное сообщение", examples=["pong"])

    @summary_aspect("Формирование ответа pong")
    async def pong(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "PingAction.Result":
        return PingAction.Result(message="pong")
