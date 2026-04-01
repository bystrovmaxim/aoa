# tests2/core/test_machine_roles.py
"""
Тесты проверки ролей в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine._check_action_roles() — первый шаг конвейера
выполнения действия. Машина читает RoleMeta из ClassMetadata (собранную
из @check_roles) и сравнивает spec с ролями пользователя в Context.

Четыре режима проверки ролей:

1. ROLE_NONE ("__NONE__") — доступ без аутентификации. Любой пользователь,
   включая анонимного (без ролей), проходит проверку. Типичное использование:
   PingAction, health check, публичные эндпоинты.

2. ROLE_ANY ("__ANY__") — требуется хотя бы одна роль. Пользователь
   обязан быть аутентифицирован (иметь хотя бы одну роль), но конкретная
   роль не важна.

3. Конкретная роль ("admin") — требуется именно эта роль. Пользователь
   должен иметь роль "admin" в своём списке ролей.

4. Список ролей (["admin", "manager"]) — требуется хотя бы одна из списка.
   Проверяется пересечение spec и user.roles.

Если действие не имеет @check_roles — TypeError (не AuthorizationError).
Это баг разработчика, а не ошибка пользователя.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

ROLE_NONE:
    - Пользователь без ролей — проходит.
    - Пользователь с ролями — проходит.

ROLE_ANY:
    - Пользователь с ролями — проходит.
    - Пользователь без ролей — AuthorizationError.

Конкретная роль:
    - Роль совпадает — проходит.
    - Роль не совпадает — AuthorizationError.

Список ролей:
    - Пересечение есть — проходит.
    - Пересечения нет — AuthorizationError.

Отсутствие @check_roles:
    - TypeError с информативным сообщением.

Интеграция с TestBench:
    - PingAction (ROLE_NONE) через bench — проходит.
    - FullAction (роль "manager") через manager_bench — проходит.
    - AdminAction (роль "admin") через admin_bench — проходит.
    - AdminAction через bench (без роли admin) — AuthorizationError.
    - FullAction через bench (без роли manager) — AuthorizationError.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_ANY, check_roles
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.core.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.testing import TestBench
from tests2.domain import AdminAction, FullAction, PingAction

# ═════════════════════════════════════════════════════════════════════════════
# Намеренно сломанные действия для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


class _MockParams(BaseParams):
    """Пустые параметры для edge-case действий."""

    pass


class _MockResult(BaseResult):
    """Пустой результат для edge-case действий."""

    pass


@meta(description="Действие с ROLE_ANY для тестов")
@check_roles(ROLE_ANY)
class _ActionRoleAny(BaseAction[_MockParams, _MockResult]):
    """Требует любую роль — пользователь должен быть аутентифицирован."""

    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Действие для менеджеров и редакторов")
@check_roles(["manager", "editor"])
class _ActionRoleList(BaseAction[_MockParams, _MockResult]):
    """Требует одну из ролей: manager или editor."""

    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Действие без @check_roles — баг разработчика")
class _ActionNoCheckRoles(BaseAction[_MockParams, _MockResult]):
    """Нет @check_roles — TypeError при выполнении."""

    @summary_aspect("test")
    async def summary(self, params, state, box, connections):
        return _MockResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """
    ActionProductMachine с тихим логгером для unit-тестов.

    LogCoordinator без логгеров — сообщения не выводятся в stdout.
    """
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context_admin() -> Context:
    """Контекст с ролями admin и user."""
    return Context(user=UserInfo(user_id="admin_1", roles=["admin", "user"]))


@pytest.fixture()
def context_manager() -> Context:
    """Контекст с ролью manager."""
    return Context(user=UserInfo(user_id="mgr_1", roles=["manager"]))


@pytest.fixture()
def context_no_roles() -> Context:
    """Контекст без ролей — анонимный пользователь."""
    return Context(user=UserInfo(user_id="guest", roles=[]))


# ═════════════════════════════════════════════════════════════════════════════
# ROLE_NONE — доступ без аутентификации
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleNone:
    """ROLE_NONE — действие доступно всем, включая анонимных."""

    def test_user_without_roles_passes(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей проходит проверку ROLE_NONE.

        PingAction объявлен с @check_roles(ROLE_NONE). Машина проверяет
        spec == "__NONE__" → _check_none_role() → всегда True.
        Роли пользователя не проверяются.
        """
        # Arrange — PingAction с ROLE_NONE, контекст без ролей
        action = PingAction()
        metadata = machine._get_metadata(action)

        # Act — проверка ролей не бросает исключений
        machine._check_action_roles(action, context_no_roles, metadata)

        # Assert — проверка прошла (отсутствие исключения = успех)

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """
        Пользователь с ролями тоже проходит ROLE_NONE.

        ROLE_NONE означает "аутентификация не требуется", а не
        "запрещено аутентифицированным". Любой пользователь проходит.
        """
        # Arrange — PingAction с ROLE_NONE, контекст с ролями admin, user
        action = PingAction()
        metadata = machine._get_metadata(action)

        # Act — проверка не бросает исключений
        machine._check_action_roles(action, context_admin, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# ROLE_ANY — требуется хотя бы одна роль
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleAny:
    """ROLE_ANY — пользователь должен быть аутентифицирован (иметь роли)."""

    def test_user_with_roles_passes(self, machine, context_admin) -> None:
        """
        Пользователь с ролями проходит ROLE_ANY.

        spec == "__ANY__" → _check_any_role() → проверяет, что
        user_roles непустой → True.
        """
        # Arrange — _ActionRoleAny с ROLE_ANY, контекст с ролями
        action = _ActionRoleAny()
        metadata = machine._get_metadata(action)

        # Act — проверка проходит
        machine._check_action_roles(action, context_admin, metadata)

    def test_user_without_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется ROLE_ANY → AuthorizationError.

        _check_any_role() проверяет if not user_roles → raise.
        Сообщение: "Authentication required: user must have at least one role".
        """
        # Arrange — _ActionRoleAny с ROLE_ANY, контекст без ролей
        action = _ActionRoleAny()
        metadata = machine._get_metadata(action)

        # Act & Assert — AuthorizationError с информативным сообщением
        with pytest.raises(AuthorizationError, match="Authentication required"):
            machine._check_action_roles(action, context_no_roles, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Конкретная роль — строка
# ═════════════════════════════════════════════════════════════════════════════


class TestSingleRole:
    """Проверка конкретной роли: spec — строка (не ROLE_NONE, не ROLE_ANY)."""

    def test_matching_role_passes(self, machine, context_admin) -> None:
        """
        Пользователь с ролью "admin" проходит проверку @check_roles("admin").

        AdminAction объявлен с @check_roles("admin"). Контекст содержит
        roles=["admin", "user"]. _check_single_role() проверяет
        "admin" in user_roles → True.
        """
        # Arrange — AdminAction с ролью "admin", контекст с admin в ролях
        action = AdminAction()
        metadata = machine._get_metadata(action)

        # Act — проверка проходит
        machine._check_action_roles(action, context_admin, metadata)

    def test_non_matching_role_rejected(self, machine, context_manager) -> None:
        """
        Пользователь с ролью "manager" отклоняется для @check_roles("admin").

        AdminAction требует "admin". Контекст содержит roles=["manager"].
        _check_single_role(): "admin" not in ["manager"] → AuthorizationError.
        """
        # Arrange — AdminAction с ролью "admin", контекст с ролью "manager"
        action = AdminAction()
        metadata = machine._get_metadata(action)

        # Act & Assert — AuthorizationError с указанием требуемой роли
        with pytest.raises(AuthorizationError, match="Required role: 'admin'"):
            machine._check_action_roles(action, context_manager, metadata)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется для @check_roles("admin").
        """
        # Arrange — AdminAction, анонимный контекст
        action = AdminAction()
        metadata = machine._get_metadata(action)

        # Act & Assert
        with pytest.raises(AuthorizationError):
            machine._check_action_roles(action, context_no_roles, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Список ролей
# ═════════════════════════════════════════════════════════════════════════════


class TestRoleList:
    """Проверка списка ролей: spec — список строк."""

    def test_intersection_passes(self, machine, context_manager) -> None:
        """
        Пользователь с ролью "manager" проходит @check_roles(["manager", "editor"]).

        _check_list_role() проверяет any(role in user_roles for role in spec).
        "manager" есть и в spec, и в user_roles → True.
        """
        # Arrange — _ActionRoleList с ["manager", "editor"], контекст с "manager"
        action = _ActionRoleList()
        metadata = machine._get_metadata(action)

        # Act — проверка проходит
        machine._check_action_roles(action, context_manager, metadata)

    def test_no_intersection_rejected(self, machine, context_admin) -> None:
        """
        Пользователь с ролями ["admin", "user"] отклоняется
        для @check_roles(["manager", "editor"]).

        Пересечение {"admin", "user"} ∩ {"manager", "editor"} = ∅ → AuthorizationError.
        """
        # Arrange — _ActionRoleList с ["manager", "editor"],
        # контекст с ["admin", "user"] — нет пересечения
        action = _ActionRoleList()
        metadata = machine._get_metadata(action)

        # Act & Assert — AuthorizationError с указанием требуемых ролей
        with pytest.raises(AuthorizationError, match="Required one of the roles"):
            machine._check_action_roles(action, context_admin, metadata)

    def test_no_roles_rejected(self, machine, context_no_roles) -> None:
        """
        Пользователь без ролей отклоняется для списка ролей.
        """
        # Arrange — _ActionRoleList, анонимный контекст
        action = _ActionRoleList()
        metadata = machine._get_metadata(action)

        # Act & Assert
        with pytest.raises(AuthorizationError):
            machine._check_action_roles(action, context_no_roles, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Отсутствие @check_roles — TypeError
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingCheckRoles:
    """Действие без @check_roles — TypeError, не AuthorizationError."""

    def test_no_decorator_raises_type_error(self, machine, context_admin) -> None:
        """
        Действие без @check_roles → TypeError при проверке ролей.

        Это баг разработчика: забыл поставить @check_roles.
        Машина бросает TypeError с указанием имени действия
        и подсказкой использовать @check_roles(ROLE_NONE).
        """
        # Arrange — _ActionNoCheckRoles без @check_roles
        action = _ActionNoCheckRoles()
        metadata = machine._get_metadata(action)

        # Act & Assert — TypeError, не AuthorizationError
        with pytest.raises(TypeError, match="does not have a @check_roles"):
            machine._check_action_roles(action, context_admin, metadata)


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с TestBench
# ═════════════════════════════════════════════════════════════════════════════


class TestRolesWithBench:
    """Проверка ролей через TestBench — полный конвейер с двумя машинами."""

    @pytest.fixture()
    def bench(self) -> TestBench:
        """TestBench без ролей (анонимный пользователь)."""
        return TestBench(log_coordinator=LogCoordinator(loggers=[]))

    @pytest.fixture()
    def manager_bench(self, bench) -> TestBench:
        """TestBench с ролью manager."""
        return bench.with_user(user_id="mgr_1", roles=["manager"])

    @pytest.fixture()
    def admin_bench(self, bench) -> TestBench:
        """TestBench с ролью admin."""
        return bench.with_user(user_id="admin_1", roles=["admin"])

    @pytest.mark.asyncio
    async def test_ping_with_anonymous_bench(self, bench) -> None:
        """
        PingAction (ROLE_NONE) проходит через bench без ролей.

        TestBench прогоняет действие на async и sync машинах.
        Обе машины проверяют роли через _check_action_roles().
        ROLE_NONE всегда проходит → результат "pong".
        """
        # Arrange — PingAction с ROLE_NONE
        action = PingAction()
        params = PingAction.Params()

        # Act — полный конвейер через bench
        result = await bench.run(action, params, rollup=False)

        # Assert — конвейер завершился успешно
        assert result.message == "pong"

    @pytest.mark.asyncio
    async def test_full_action_with_manager_bench(self, manager_bench) -> None:
        """
        FullAction (роль "manager") проходит через manager_bench.

        FullAction требует @check_roles("manager"). manager_bench
        содержит пользователя с roles=["manager"].
        """
        # Arrange — FullAction с ролью "manager", мок db для connections
        from unittest.mock import AsyncMock

        from tests2.domain import NotificationService, PaymentService, TestDbManager

        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-BENCH"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        bench_with_mocks = manager_bench.with_mocks({
            PaymentService: mock_payment,
            NotificationService: mock_notification,
        })

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act — полный конвейер
        result = await bench_with_mocks.run(
            action, params, rollup=False, connections={"db": mock_db},
        )

        # Assert — конвейер завершился, результат содержит данные
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_admin_action_rejected_without_admin_role(self, bench) -> None:
        """
        AdminAction (роль "admin") отклоняется через bench без ролей.

        bench содержит анонимного пользователя (roles=["tester"]).
        AdminAction требует "admin" → AuthorizationError.
        """
        # Arrange — AdminAction, bench без роли admin
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act & Assert — AuthorizationError от машины
        with pytest.raises(AuthorizationError):
            await bench.run(action, params, rollup=False)

    @pytest.mark.asyncio
    async def test_admin_action_passes_with_admin_bench(self, admin_bench) -> None:
        """
        AdminAction (роль "admin") проходит через admin_bench.

        admin_bench содержит пользователя с roles=["admin"].
        """
        # Arrange — AdminAction, admin_bench с ролью admin
        action = AdminAction()
        params = AdminAction.Params(target="user_456")

        # Act — полный конвейер
        result = await admin_bench.run(action, params, rollup=False)

        # Assert — результат содержит данные
        assert result.success is True
        assert result.target == "user_456"
