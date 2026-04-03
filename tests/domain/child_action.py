# tests/domain/child_action.py
"""
ChildAction — дочернее действие для тестирования вложенных вызовов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Действие, предназначенное для вызова из другого действия через box.run().
Содержит один regular-аспект и summary. Не имеет зависимостей и connections.
Доступно всем (ROLE_NONE). Принадлежит SystemDomain.

Аспект process_aspect принимает строковое значение из params и возвращает
его с префиксом "processed:". Summary формирует Result из state.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

- Тесты вложенности: корневое действие вызывает ChildAction через
  box.run(ChildAction, ChildAction.Params(value="test")).
- Тесты nest_level: при вложенном вызове nest_level увеличивается.
- Тесты WrapperConnectionManager: при передаче connections в box.run()
  дочернее действие получает обёрнутые менеджеры.
- Тесты rollup: rollup прокидывается через box.run() в дочернее действие.

    # Вызов из аспекта другого действия:
    async def some_aspect(self, params, state, box, connections):
        child_result = await box.run(
            ChildAction,
            ChildAction.Params(value="hello"),
        )
        assert child_result.processed == "processed:hello"

    # Прямой вызов через TestBench:
    result = await bench.run(
        ChildAction(),
        ChildAction.Params(value="world"),
        rollup=False,
    )
    assert result.processed == "processed:world"
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

from .domains import SystemDomain


@meta(description="Дочернее действие для вложенных вызовов", domain=SystemDomain)
@check_roles(ROLE_NONE)
class ChildAction(BaseAction["ChildAction.Params", "ChildAction.Result"]):
    """
    Действие для вложенных вызовов через box.run().

    Конвейер:
    1. process_aspect (regular) — добавляет префикс "processed:" к значению.
       Чекер: result_string("processed_value", required=True).
    2. build_result_summary (summary) — формирует Result из state.
    """

    class Params(BaseParams):
        """Параметры дочернего действия — строковое значение для обработки."""
        value: str = Field(
            description="Значение для обработки",
            examples=["test_value"],
        )

    class Result(BaseResult):
        """Результат дочернего действия — обработанное значение."""
        processed: str = Field(description="Обработанное значение с префиксом")

    @regular_aspect("Обработка значения")
    @result_string("processed_value", required=True)
    async def process_aspect(
        self,
        params: "ChildAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Добавляет префикс "processed:" к значению из params.

        Возвращает:
            dict с ключом processed_value.
        """
        return {"processed_value": f"processed:{params.value}"}

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: "ChildAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "ChildAction.Result":
        """
        Формирует Result из processed_value в state.

        Возвращает:
            ChildAction.Result с полем processed.
        """
        return ChildAction.Result(processed=state["processed_value"])
