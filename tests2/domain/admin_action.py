# tests2/domain/admin_action.py
"""
AdminAction — действие с ограниченным доступом (роль "admin").

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Действие, доступное только пользователям с ролью "admin". Содержит
один regular-аспект с чекером и summary. Не имеет зависимостей
и connections. Принадлежит SystemDomain.

Аспект execute_admin формирует строку с префиксом "admin_processed:"
и записывает её в state как admin_note. Summary формирует Result
с флагом success=True и целевым объектом из params.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

- Тесты ролей: пользователь с ролью "admin" проходит, пользователь
  с ролью "user" или без ролей — AuthorizationError.
- Тесты check_roles с конкретной ролью (не ROLE_NONE, не ROLE_ANY,
  не список ролей).
- Тесты run_aspect: выполнение execute_admin отдельно.

    # Успешный вызов:
    admin_bench = bench.with_user(user_id="admin_1", roles=["admin"])
    result = await admin_bench.run(
        AdminAction(),
        AdminAction.Params(target="user_456"),
        rollup=False,
    )
    assert result.success is True
    assert result.target == "user_456"

    # Отказ в доступе:
    user_bench = bench.with_user(user_id="user_1", roles=["user"])
    with pytest.raises(AuthorizationError):
        await user_bench.run(
            AdminAction(),
            AdminAction.Params(target="user_456"),
            rollup=False,
        )
"""

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import check_roles
from action_machine.checkers import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import SystemDomain


@meta(description="Административное действие с ограниченным доступом", domain=SystemDomain)
@check_roles("admin")
class AdminAction(BaseAction["AdminAction.Params", "AdminAction.Result"]):
    """
    Действие, доступное только администраторам.

    Конвейер:
    1. execute_admin (regular) — формирует admin_note с префиксом.
       Чекер: result_string("admin_note", required=True).
    2. build_result (summary) — формирует Result с success и target.
    """

    class Params(BaseParams):
        """Параметры административного действия — целевой объект операции."""
        target: str = Field(
            description="Целевой объект для административной операции",
            examples=["user_456"],
        )

    class Result(BaseResult):
        """Результат административного действия."""
        success: bool = Field(description="Успешность выполнения операции")
        target: str = Field(description="Обработанный целевой объект")

    @regular_aspect("Выполнение административной операции")
    @result_string("admin_note", required=True)
    async def execute_admin(
        self,
        params: "AdminAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Выполняет административную операцию над целевым объектом.

        Формирует строку admin_note с префиксом "admin_processed:"
        и целевым объектом из params.

        Возвращает:
            dict с ключом admin_note.
        """
        return {"admin_note": f"admin_processed:{params.target}"}

    @summary_aspect("Формирование результата")
    async def build_result(
        self,
        params: "AdminAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "AdminAction.Result":
        """
        Формирует результат административного действия.

        Возвращает:
            AdminAction.Result с success=True и target из params.
        """
        return AdminAction.Result(
            success=True,
            target=params.target,
        )
