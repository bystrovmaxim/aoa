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
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.core.exceptions import AuthorizationError
from action_machine.testing import MockAction, TestBench
from tests.domain import (
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
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        result = await clean_bench.run(action, params, rollup=False)

        # Assert
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
        # Arrange
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=500.0)

        # Act
        result = await manager_bench.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        # Assert
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
        # Arrange
        expected = PingAction.Result(message="direct")
        mock = MockAction(result=expected)

        # Act
        result = await clean_bench.run(mock, PingAction.Params(), rollup=False)

        # Assert
        assert result is expected
        assert mock.call_count == 1


class TestRoleCheck:
    """Ролевая проверка использует пользователя из TestBench."""

    @pytest.mark.anyio
    async def test_default_user_rejected_by_admin_action(
        self, clean_bench: TestBench,
    ) -> None:
        """
        Дефолтный пользователь — roles=["tester"]. AdminAction
        требует "admin". Проверка ролей отклоняет.
        """
        # Arrange
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act & Assert
        with pytest.raises(AuthorizationError):
            await clean_bench.run(action, params, rollup=False)

    @pytest.mark.anyio
    async def test_with_user_grants_admin_access(
        self, admin_bench: TestBench,
    ) -> None:
        """
        admin_bench создаёт пользователя с ролью "admin".
        AdminAction проходит проверку ролей.
        """
        # Arrange
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act
        result = await admin_bench.run(action, params, rollup=False)

        # Assert
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
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act & Assert
        with pytest.raises(TypeError):
            await clean_bench.run(action, params)  # type: ignore[call-arg]
