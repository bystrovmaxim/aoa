# tests/bench/test_bench_run.py
"""
Тесты TestBench.run() — полный прогон действия на async и sync машинах.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Действие без зависимостей (PingAction) выполняется и возвращает результат.
- Действие с зависимостями (FullAction) получает моки через box.resolve().
- MockAction выполняется напрямую, минуя конвейер.
- Ролевая проверка использует пользователя из TestBench.
- with_user(admin) даёт доступ к AdminAction.
- rollup — обязательный параметр без дефолта.

Все core-типы (Params, Result, State) — неизменяемы. Результаты сравниваются
через model_dump() или прямое сравнение полей.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.model.exceptions import AuthorizationError
from action_machine.testing import MockAction, TestBench
from tests.domain_model import (
    AdminAction,
    FullAction,
    PingAction,
)


class TestSimpleAction:
    """Прогон действий без зависимостей."""

    @pytest.mark.anyio
    async def test_ping_returns_pong(self, clean_bench: TestBench) -> None:
        """
        PingAction не имеет зависимостей и regular-аспектов.
        TestBench выполняет summary и возвращает PingResult.
        """
        action = PingAction()
        params = PingAction.Params()

        result = await clean_bench.run(action, params, rollup=False)

        assert isinstance(result, PingAction.Result)
        assert result.message == "pong"


class TestActionWithDependencies:
    """Прогон действий с моками зависимостей."""

    @pytest.mark.anyio
    async def test_full_action_uses_mocks(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        FullAction получает моки PaymentService и NotificationService
        через box.resolve(). Результат формируется из state,
        накопленного regular-аспектами.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=500.0)

        result = await manager_bench.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        # Проверка полей результата (frozen)
        assert result.order_id == "ORD-u1"
        assert result.status == "created"
        assert result.total == 500.0
        assert result.txn_id == "TXN-TEST-001"


class TestMockAction:
    """MockAction выполняется напрямую, минуя конвейер."""

    @pytest.mark.anyio
    async def test_bypasses_pipeline(self, clean_bench: TestBench) -> None:
        """
        MockAction не имеет @meta и @check_roles. Если TestBench
        прогонит его через конвейер — TypeError от проверки ролей.
        Прямой вызов через .run() обходит конвейер.
        """
        expected = PingAction.Result(message="direct")
        mock = MockAction(result=expected)

        result = await clean_bench.run(mock, PingAction.Params(), rollup=False)

        assert result is expected
        assert mock.call_count == 1


class TestRoleCheck:
    """Ролевая проверка использует пользователя из TestBench."""

    @pytest.mark.anyio
    async def test_default_user_rejected_by_admin_action(
        self, clean_bench: TestBench,
    ) -> None:
        """
        Дефолтный пользователь — StubTesterRole. AdminAction
        требует AdminRole. Проверка ролей отклоняет.
        """
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        with pytest.raises(AuthorizationError):
            await clean_bench.run(action, params, rollup=False)

    @pytest.mark.anyio
    async def test_with_user_grants_admin_access(
        self, admin_bench: TestBench,
    ) -> None:
        """
        admin_bench создаёт пользователя с AdminRole.
        AdminAction проходит проверку ролей.
        """
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        result = await admin_bench.run(action, params, rollup=False)

        assert result.success is True
        assert result.target == "user_456"


class TestRollupRequired:
    """rollup — обязательный параметр без значения по умолчанию."""

    @pytest.mark.anyio
    async def test_missing_rollup_raises_type_error(
        self, clean_bench: TestBench,
    ) -> None:
        """
        Если дефолт появится — тестировщик может случайно пропустить
        rollup и не заметить, что тестирует в неправильном режиме.
        """
        action = PingAction()
        params = PingAction.Params()

        with pytest.raises(TypeError):
            await clean_bench.run(action, params)  # type: ignore[call-arg]
