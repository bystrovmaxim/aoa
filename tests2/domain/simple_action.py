# tests2/domain/simple_action.py
"""
SimpleAction — действие средней сложности с одним regular-аспектом.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Действие с одним regular-аспектом и одним summary-аспектом. Regular-аспект
валидирует входное имя и записывает validated_name в state. Чекер
result_string гарантирует, что validated_name — непустая строка.

Не имеет зависимостей и connections. Доступно всем (ROLE_NONE).
Принадлежит OrdersDomain.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

- Тесты чекеров: result_string проверяет validated_name.
- Тесты run_aspect: выполнение validate_name отдельно.
- Тесты run_summary: передача state с validated_name в summary.
- Тесты базового конвейера: regular → state → summary → result.

    result = await bench.run(
        SimpleAction(),
        SimpleAction.Params(name="Alice"),
        rollup=False,
    )
    assert result.greeting == "Hello, Alice!"
"""

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import OrdersDomain


@meta(description="Простое действие с одним аспектом", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class SimpleAction(BaseAction["SimpleAction.Params", "SimpleAction.Result"]):
    """
    Действие с одним regular-аспектом и чекером.

    Конвейер:
    1. validate_name (regular) — записывает validated_name в state.
       Чекер: result_string("validated_name", required=True, min_length=1).
    2. build_greeting (summary) — формирует приветствие из state.
    """

    class Params(BaseParams):
        """Параметры SimpleAction — имя для обработки."""
        name: str = Field(
            description="Имя для обработки",
            min_length=1,
            examples=["Alice"],
        )

    class Result(BaseResult):
        """Результат SimpleAction — приветственное сообщение."""
        greeting: str = Field(description="Приветственное сообщение")

    @regular_aspect("Валидация имени")
    @result_string("validated_name", required=True, min_length=1)
    async def validate_name(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Валидирует и нормализует имя из параметров.

        Записывает в state поле validated_name — имя без пробелов
        по краям. Чекер result_string проверяет, что результат —
        непустая строка длиной >= 1.

        Возвращает:
            dict с ключом validated_name.
        """
        return {"validated_name": params.name.strip()}

    @summary_aspect("Формирование приветствия")
    async def build_greeting(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "SimpleAction.Result":
        """
        Формирует приветственное сообщение из validated_name в state.

        Возвращает:
            SimpleAction.Result с полем greeting = "Hello, {name}!".
        """
        name = state["validated_name"]
        return SimpleAction.Result(greeting=f"Hello, {name}!")
