# tests/testing/test_bench.py
"""
Тесты для TestBench — тестовой машины ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание тестовой машины:
    - Без аргументов — рабочий объект с дефолтами.
    - С моками — сервис-зависимости доступны через box.resolve().

Иммутабельность (fluent-методы):
    - with_user() не меняет оригинал.
    - with_mocks() не меняет оригинал.
    - with_runtime() не меняет оригинал.
    - with_request() не меняет оригинал.
    - Цепочка fluent-вызовов не ломает промежуточные шаги.

run() — полный прогон:
    - Действие без зависимостей выполняется и возвращает результат.
    - Действие с зависимостями получает мок через box.resolve().
    - MockAction выполняется напрямую, минуя конвейер.
    - Ролевая проверка использует пользователя из тестовой машины.
    - with_user(admin) даёт доступ к admin-действиям.
    - rollup — обязательный параметр без дефолта.

run_aspect() — один аспект:
    - Выполняет указанный regular-аспект и возвращает его dict.
    - Невалидный state отклоняется до выполнения аспекта.
    - Несуществующий аспект — ValueError.
    - Первый аспект принимает пустой state.

run_summary() — только summary:
    - Выполняет summary и возвращает результат.
    - Неполный state отклоняется до выполнения.
    - Действие без summary — ValueError.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_float, result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.dependencies.depends import depends
from action_machine.testing import MockAction, TestBench
from action_machine.testing.state_validator import StateValidationError

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые сервисы
# ═════════════════════════════════════════════════════════════════════════════


class PaymentService:
    """Имитация платёжного шлюза."""

    def charge(self, amount: float) -> str:
        return f"TXN-{amount}"


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    """Параметры без полей."""
    pass


class PingResult(BaseResult):
    """Результат с полем message."""
    message: str = Field(default="pong", description="Ответ")


class OrderParams(BaseParams):
    """Параметры заказа."""
    user_id: str = Field(description="ID пользователя", min_length=1)
    amount: float = Field(description="Сумма", gt=0)


class OrderResult(BaseResult):
    """Результат заказа."""
    order_id: str = Field(default="", description="ID заказа")
    status: str = Field(default="", description="Статус")
    total: float = Field(default=0.0, description="Итого")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые действия
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Пинг")
@check_roles(ROLE_NONE)
class PingAction(BaseAction[EmptyParams, PingResult]):
    """Простейшее действие — один summary, без зависимостей."""

    @summary_aspect("pong")
    async def pong(self, params, state, box, connections):
        """Фиксированный ответ."""
        return PingResult(message="pong")


@meta(description="Создание заказа")
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Платёжный шлюз")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    """
    validate → validated_user (str, required, min_length=1)
    process  → txn_id (str, required), charged_amount (float, required, ≥0)
    summary  → OrderResult из state
    """

    @regular_aspect("Валидация")
    @result_string("validated_user", required=True, min_length=1)
    async def validate(self, params, state, box, connections):
        """Записывает validated_user в state."""
        return {"validated_user": params.user_id}

    @regular_aspect("Платёж")
    @result_string("txn_id", required=True)
    @result_float("charged_amount", required=True, min_value=0.0)
    async def process(self, params, state, box, connections):
        """Списывает через PaymentService."""
        payment = box.resolve(PaymentService)
        txn_id = payment.charge(params.amount)
        return {"txn_id": txn_id, "charged_amount": params.amount}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        """Собирает OrderResult из state."""
        return OrderResult(
            order_id=f"ORD-{state['validated_user']}",
            status="created",
            total=state["charged_amount"],
        )


@meta(description="Только для админов")
@check_roles("admin")
class AdminOnlyAction(BaseAction[EmptyParams, PingResult]):
    """Требует роль admin."""

    @summary_aspect("admin ok")
    async def summary(self, params, state, box, connections):
        """Доступно только админам."""
        return PingResult(message="admin_ok")


@meta(description="Только summary")
@check_roles(ROLE_NONE)
class SummaryOnlyAction(BaseAction[EmptyParams, PingResult]):
    """Нет regular-аспектов."""

    @summary_aspect("Прямой результат")
    async def build_result(self, params, state, box, connections):
        """Не зависит от state."""
        return PingResult(message="summary_only")


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_payment() -> PaymentService:
    return PaymentService()


@pytest.fixture
def bench(mock_payment) -> TestBench:
    """Тестовая машина с моком PaymentService."""
    return TestBench(
        mocks={PaymentService: mock_payment},
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def clean_bench() -> TestBench:
    """Тестовая машина без моков."""
    return TestBench(log_coordinator=AsyncMock())


# ═════════════════════════════════════════════════════════════════════════════
# Создание тестовой машины
# ═════════════════════════════════════════════════════════════════════════════


class TestCreation:

    def test_without_arguments(self):
        """
        Проверяет, что тестовая машина создаётся без аргументов:

        1. coordinator — экземпляр GateCoordinator, готовый к работе.
        2. mocks — пустой словарь.
        3. plugins — пустой список.

        Это минимальная конфигурация для тестирования действий без зависимостей.
        """
        b = TestBench()
        assert isinstance(b.coordinator, GateCoordinator)
        assert b.mocks == {}
        assert b.plugins == []

    def test_with_service_mock(self, mock_payment):
        """
        Проверяет, что мок сервиса сохраняется как есть:

        PaymentService — обычный объект с методом charge(). Тестовая машина
        не должна оборачивать его — аспект вызывает payment.charge() напрямую.
        """
        b = TestBench(mocks={PaymentService: mock_payment})
        assert b._prepared_mocks[PaymentService] is mock_payment


# ═════════════════════════════════════════════════════════════════════════════
# Иммутабельность (fluent-методы)
# ═════════════════════════════════════════════════════════════════════════════


class TestImmutability:

    def test_with_user(self, clean_bench):
        """
        Проверяет иммутабельность with_user():

        1. Оригинальная машина сохраняет user_id="test_user" после вызова.
        2. Новая машина содержит user_id="admin".
        3. Новая машина — другой объект (не self).

        Если with_user() мутирует оригинал — параллельные тесты с разными
        пользователями будут ломать друг друга.
        """
        new = clean_bench.with_user(user_id="admin", roles=["admin"])

        assert new is not clean_bench
        assert clean_bench._build_context().user.user_id == "test_user"
        assert new._build_context().user.user_id == "admin"
        assert new._build_context().user.roles == ["admin"]

    def test_with_mocks(self, clean_bench):
        """
        Проверяет иммутабельность with_mocks():

        1. Оригинальная машина сохраняет пустые моки после вызова.
        2. Новая машина содержит переданный мок.
        """
        new = clean_bench.with_mocks({PaymentService: PaymentService()})

        assert clean_bench.mocks == {}
        assert PaymentService in new.mocks

    def test_with_runtime(self, clean_bench):
        """
        Проверяет иммутабельность with_runtime():

        Оригинальная машина сохраняет hostname="test-host" после вызова.
        """
        clean_bench.with_runtime(hostname="prod-01")
        assert clean_bench._build_context().runtime.hostname == "test-host"

    def test_with_request(self, clean_bench):
        """
        Проверяет иммутабельность with_request():

        Оригинальная машина сохраняет trace_id="test-trace-000" после вызова.
        """
        clean_bench.with_request(trace_id="custom")
        assert clean_bench._build_context().request.trace_id == "test-trace-000"

    def test_chain(self, clean_bench):
        """
        Проверяет, что цепочка fluent-вызовов не ломает промежуточные шаги:

        step1 = bench.with_user(...)
        step2 = step1.with_request(...)

        step1 не должен получить request от step2.
        """
        step1 = clean_bench.with_user(user_id="step1")
        step2 = step1.with_request(trace_id="step2_trace")

        assert step1._build_context().request.trace_id == "test-trace-000"
        assert step2._build_context().request.trace_id == "step2_trace"
        assert step2._build_context().user.user_id == "step1"


# ═════════════════════════════════════════════════════════════════════════════
# run() — полный прогон
# ═════════════════════════════════════════════════════════════════════════════


class TestRun:

    @pytest.mark.anyio
    async def test_simple_action(self, clean_bench):
        """
        Проверяет полный прогон простого действия:

        PingAction не имеет зависимостей и regular-аспектов.
        Тестовая машина должна выполнить summary и вернуть PingResult.
        """
        result = await clean_bench.run(PingAction(), EmptyParams(), rollup=False)
        assert isinstance(result, PingResult)
        assert result.message == "pong"

    @pytest.mark.anyio
    async def test_action_with_mock_dependency(self, bench):
        """
        Проверяет, что мок сервиса доступен через box.resolve() внутри аспекта:

        1. validate записывает validated_user в state.
        2. process вызывает box.resolve(PaymentService).charge() — получает мок.
        3. summary собирает OrderResult из state.

        Если мок не попадает в resources — process падает с "Dependency not declared".
        """
        result = await bench.run(
            CreateOrderAction(),
            OrderParams(user_id="u1", amount=500.0),
            rollup=False,
        )
        assert result.order_id == "ORD-u1"
        assert result.status == "created"
        assert result.total == 500.0

    @pytest.mark.anyio
    async def test_mock_action_bypasses_pipeline(self, clean_bench):
        """
        Проверяет, что MockAction выполняется напрямую через .run():

        MockAction не имеет @meta и @check_roles. Если тестовая машина
        прогонит его через конвейер — TypeError от проверки ролей.
        """
        expected = PingResult(message="direct")
        mock = MockAction(result=expected)
        result = await clean_bench.run(mock, EmptyParams(), rollup=False)
        assert result is expected
        assert mock.call_count == 1

    @pytest.mark.anyio
    async def test_role_check_uses_bench_user(self, clean_bench):
        """
        Проверяет, что ролевая проверка использует пользователя из тестовой машины:

        Дефолтный пользователь — roles=["tester"]. AdminOnlyAction требует "admin".
        Тестовая машина должна прокинуть user в контекст, и проверка ролей отклонит.
        """
        with pytest.raises(AuthorizationError):
            await clean_bench.run(AdminOnlyAction(), EmptyParams(), rollup=False)

    @pytest.mark.anyio
    async def test_with_user_grants_access(self, clean_bench):
        """
        Проверяет, что with_user() влияет на проверку ролей:

        bench.with_user(roles=["admin"]) создаёт машину с админом.
        AdminOnlyAction должен пройти.
        """
        admin_bench = clean_bench.with_user(user_id="boss", roles=["admin"])
        result = await admin_bench.run(AdminOnlyAction(), EmptyParams(), rollup=False)
        assert result.message == "admin_ok"

    @pytest.mark.anyio
    async def test_rollup_is_required(self, clean_bench):
        """
        Проверяет, что rollup — обязательный параметр без значения по умолчанию:

        Если дефолт появится — тестировщик может случайно пропустить rollup
        и не заметить, что тестирует в неправильном режиме.
        """
        with pytest.raises(TypeError):
            await clean_bench.run(PingAction(), EmptyParams())  # type: ignore[call-arg]


# ═════════════════════════════════════════════════════════════════════════════
# run_aspect() — один аспект
# ═════════════════════════════════════════════════════════════════════════════


class TestRunAspect:

    @pytest.mark.anyio
    async def test_executes_single_aspect(self, bench):
        """
        Проверяет, что run_aspect() выполняет только указанный аспект:

        validate — первый аспект CreateOrderAction. Должен вернуть
        {"validated_user": "u1"} без выполнения process и summary.
        """
        result = await bench.run_aspect(
            CreateOrderAction(), "validate",
            OrderParams(user_id="u1", amount=100.0),
            state={},
            rollup=False,
        )
        assert result == {"validated_user": "u1"}

    @pytest.mark.anyio
    async def test_second_aspect_with_valid_state(self, bench):
        """
        Проверяет, что run_aspect() передаёт state в аспект:

        process зависит от validated_user в state. Передаём корректный state —
        process вызывает PaymentService.charge() и возвращает txn_id.
        """
        result = await bench.run_aspect(
            CreateOrderAction(), "process",
            OrderParams(user_id="u1", amount=250.0),
            state={"validated_user": "u1"},
            rollup=False,
        )
        assert result["txn_id"] == "TXN-250.0"
        assert result["charged_amount"] == 250.0

    @pytest.mark.anyio
    async def test_invalid_state_rejected_before_execution(self, bench):
        """
        Проверяет, что невалидный state отклоняется ДО выполнения аспекта:

        process ожидает validated_user от validate. Пустой state —
        StateValidationError, а не KeyError из кода аспекта.
        """
        with pytest.raises(StateValidationError, match="validated_user"):
            await bench.run_aspect(
                CreateOrderAction(), "process",
                OrderParams(user_id="u1", amount=100.0),
                state={},
                rollup=False,
            )

    @pytest.mark.anyio
    async def test_wrong_type_in_state_rejected(self, bench):
        """
        Проверяет, что state с неверным типом поля отклоняется:

        validated_user=123 вместо строки — чекер отклоняет до выполнения аспекта.
        """
        with pytest.raises(StateValidationError, match="должен быть строкой"):
            await bench.run_aspect(
                CreateOrderAction(), "process",
                OrderParams(user_id="u1", amount=100.0),
                state={"validated_user": 123},
                rollup=False,
            )

    @pytest.mark.anyio
    async def test_nonexistent_aspect(self, bench):
        """
        Проверяет, что несуществующий аспект даёт понятную ошибку:

        "nonexistent" нет в CreateOrderAction — StateValidationError с перечислением доступных.
        Ошибка приходит от валидатора state, который первым проверяет существование аспекта.
        """
        with pytest.raises(StateValidationError, match="не найден"):
            await bench.run_aspect(
                CreateOrderAction(), "nonexistent",
                OrderParams(user_id="u1", amount=100.0),
                state={},
                rollup=False,
            )

    @pytest.mark.anyio
    async def test_first_aspect_accepts_empty_state(self, bench):
        """
        Проверяет, что первый аспект принимает пустой state:

        validate — первый в конвейере, перед ним нет аспектов.
        Пустой state допустим — нет чекеров для проверки.
        """
        result = await bench.run_aspect(
            CreateOrderAction(), "validate",
            OrderParams(user_id="test", amount=50.0),
            state={},
            rollup=False,
        )
        assert "validated_user" in result


# ═════════════════════════════════════════════════════════════════════════════
# run_summary() — только summary
# ═════════════════════════════════════════════════════════════════════════════


class TestRunSummary:

    @pytest.mark.anyio
    async def test_executes_summary_with_complete_state(self, bench):
        """
        Проверяет, что run_summary() передаёт state в summary-аспект:

        build_result читает validated_user и charged_amount из state
        и собирает OrderResult.
        """
        result = await bench.run_summary(
            CreateOrderAction(),
            OrderParams(user_id="u1", amount=300.0),
            state={
                "validated_user": "u1",
                "txn_id": "TXN-300.0",
                "charged_amount": 300.0,
            },
            rollup=False,
        )
        assert result.order_id == "ORD-u1"
        assert result.total == 300.0

    @pytest.mark.anyio
    async def test_incomplete_state_rejected(self, bench):
        """
        Проверяет, что неполный state отклоняется до выполнения summary:

        state содержит только validated_user, но не содержит полей от аспекта process
        (txn_id, charged_amount). Валидатор обнаруживает первое отсутствующее поле.
        """
        with pytest.raises(StateValidationError, match="от аспекта 'process'"):
            await bench.run_summary(
                CreateOrderAction(),
                OrderParams(user_id="u1", amount=100.0),
                state={"validated_user": "u1"},
                rollup=False,
            )

    @pytest.mark.anyio
    async def test_summary_only_action(self, clean_bench):
        """
        Проверяет, что действие без regular-аспектов принимает пустой state:

        SummaryOnlyAction не имеет regular-аспектов — нечего валидировать.
        """
        result = await clean_bench.run_summary(
            SummaryOnlyAction(),
            EmptyParams(),
            state={},
            rollup=False,
        )
        assert result.message == "summary_only"

    @pytest.mark.anyio
    async def test_wrong_type_in_state_rejected(self, bench):
        """
        Проверяет, что state с неверным типом поля отклоняется:

        charged_amount="строка" вместо float — чекер отклоняет до выполнения.
        """
        with pytest.raises(StateValidationError, match="charged_amount"):
            await bench.run_summary(
                CreateOrderAction(),
                OrderParams(user_id="u1", amount=100.0),
                state={
                    "validated_user": "u1",
                    "txn_id": "TXN-1",
                    "charged_amount": "не число",
                },
                rollup=False,
            )

    @pytest.mark.anyio
    async def test_rollup_is_required(self, clean_bench):
        """
        Проверяет, что rollup — обязательный параметр:

        Вызов без rollup — TypeError.
        """
        with pytest.raises(TypeError):
            await clean_bench.run_summary(  # type: ignore[call-arg]
                SummaryOnlyAction(),
                EmptyParams(),
                state={},
            )
