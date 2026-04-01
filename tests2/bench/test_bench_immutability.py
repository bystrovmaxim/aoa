# tests2/bench/test_bench_immutability.py
"""
Тесты иммутабельности TestBench — fluent-методы не мутируют оригинал.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- with_user() создаёт новый объект, оригинал сохраняет дефолтного пользователя.
- with_mocks() создаёт новый объект, оригинал сохраняет пустые моки.
- with_runtime() создаёт новый объект, оригинал сохраняет дефолтный hostname.
- with_request() создаёт новый объект, оригинал сохраняет дефолтный trace_id.
- Цепочка fluent-вызовов: каждый шаг независим от последующих.

Иммутабельность критична для параллельных тестов: если with_user()
мутирует оригинал, тесты с разными пользователями ломают друг друга.
"""

from action_machine.testing import TestBench
from tests2.domain import PaymentService


class TestWithUser:
    """with_user() не мутирует оригинальный TestBench."""

    def test_returns_new_object(self, clean_bench: TestBench) -> None:
        """
        with_user() возвращает НОВЫЙ TestBench, а не self.
        Это гарантирует, что оригинал не затронут.
        """
        # Arrange & Act
        new = clean_bench.with_user(user_id="admin", roles=["admin"])

        # Assert
        assert new is not clean_bench

    def test_original_user_unchanged(self, clean_bench: TestBench) -> None:
        """
        После with_user() оригинал сохраняет дефолтного пользователя
        user_id="test_user" из UserInfoStub.
        """
        # Arrange & Act
        clean_bench.with_user(user_id="admin", roles=["admin"])

        # Assert — оригинал не изменился
        assert clean_bench._build_context().user.user_id == "test_user"

    def test_new_bench_has_new_user(self, clean_bench: TestBench) -> None:
        """
        Новый TestBench содержит переданного пользователя.
        """
        # Arrange & Act
        new = clean_bench.with_user(user_id="admin", roles=["admin"])

        # Assert
        assert new._build_context().user.user_id == "admin"
        assert new._build_context().user.roles == ["admin"]


class TestWithMocks:
    """with_mocks() не мутирует оригинальный TestBench."""

    def test_original_mocks_unchanged(self, clean_bench: TestBench) -> None:
        """
        После with_mocks() оригинал сохраняет пустые моки.
        """
        # Arrange & Act
        clean_bench.with_mocks({PaymentService: PaymentService()})

        # Assert
        assert clean_bench.mocks == {}

    def test_new_bench_has_new_mocks(self, clean_bench: TestBench) -> None:
        """
        Новый TestBench содержит переданные моки.
        """
        # Arrange & Act
        new = clean_bench.with_mocks({PaymentService: PaymentService()})

        # Assert
        assert PaymentService in new.mocks


class TestWithRuntime:
    """with_runtime() не мутирует оригинальный TestBench."""

    def test_original_runtime_unchanged(self, clean_bench: TestBench) -> None:
        """
        После with_runtime() оригинал сохраняет hostname="test-host"
        из RuntimeInfoStub.
        """
        # Arrange & Act
        clean_bench.with_runtime(hostname="prod-01")

        # Assert
        assert clean_bench._build_context().runtime.hostname == "test-host"


class TestWithRequest:
    """with_request() не мутирует оригинальный TestBench."""

    def test_original_request_unchanged(self, clean_bench: TestBench) -> None:
        """
        После with_request() оригинал сохраняет trace_id="test-trace-000"
        из RequestInfoStub.
        """
        # Arrange & Act
        clean_bench.with_request(trace_id="custom")

        # Assert
        assert clean_bench._build_context().request.trace_id == "test-trace-000"


class TestChain:
    """Цепочка fluent-вызовов: каждый шаг независим от последующих."""

    def test_intermediate_steps_independent(self, clean_bench: TestBench) -> None:
        """
        step1 = bench.with_user(...)
        step2 = step1.with_request(...)

        step1 НЕ должен получить request от step2.
        step2 должен унаследовать user от step1.
        """
        # Arrange & Act
        step1 = clean_bench.with_user(user_id="step1")
        step2 = step1.with_request(trace_id="step2_trace")

        # Assert — step1 сохранил дефолтный request
        assert step1._build_context().request.trace_id == "test-trace-000"
        # Assert — step2 получил и user от step1, и свой request
        assert step2._build_context().request.trace_id == "step2_trace"
        assert step2._build_context().user.user_id == "step1"
