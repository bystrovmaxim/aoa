# tests/core/test_base_action_machine.py
"""
Тесты BaseActionMachine.sync_run.
Покрываем строки 87-98:
- Нормальный вызов вне event loop
- Ошибка при вызове внутри event loop
"""
import warnings

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockParams(BaseParams):
    pass


class MockResult(BaseResult):
    pass


@CheckRoles(CheckRoles.NONE, desc="")
class SimpleAction(BaseAction[MockParams, MockResult]):
    @summary_aspect("test")
    async def summary(self, params, state, deps, connections):
        return MockResult()


# ----------------------------------------------------------------------
# Тесты
# ----------------------------------------------------------------------
class TestSyncRun:
    """Тесты синхронной обёртки sync_run."""

    def test_sync_run_outside_event_loop_returns_result(self):
        """sync_run вне async-контекста выполняет действие и возвращает результат."""
        machine = ActionProductMachine(Context())
        action = SimpleAction()
        params = MockParams()
        result = machine.sync_run(action, params)
        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_sync_run_inside_event_loop_raises_runtime_error(self):
        """
        sync_run внутри работающего event loop бросает RuntimeError.
        Из-за особенности реализации except RuntimeError в sync_run
        наружу вылетает сообщение от asyncio.run().
        Warning о невызванной корутине подавляется — это ожидаемое поведение.
        """
        machine = ActionProductMachine(Context())
        action = SimpleAction()
        params = MockParams()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(RuntimeError, match="cannot be called from a running event loop"):
                machine.sync_run(action, params)