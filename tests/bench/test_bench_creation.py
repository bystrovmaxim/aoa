# tests/bench/test_bench_creation.py
"""
Тесты создания TestBench — хранение параметров и дефолты.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Создание без аргументов — рабочий объект с дефолтами.
- coordinator — экземпляр GateCoordinator.
- mocks — пустой словарь по умолчанию.
- plugins — пустой список по умолчанию.
- Мок сервиса (обычный объект) сохраняется как есть в _prepared_mocks.
- AsyncMock сохраняется как есть (не оборачивается в MockAction).
"""

from unittest.mock import AsyncMock

from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.testing import TestBench
from tests.domain_model import PaymentService


class TestWithoutArguments:
    """TestBench создаётся без аргументов с разумными дефолтами."""

    def test_coordinator_is_gate_coordinator(self) -> None:
        """
        coordinator — экземпляр GateCoordinator, готовый к работе.
        Позволяет регистрировать и собирать метаданные Action.
        """
        # Arrange & Act
        b = TestBench()

        # Assert
        assert isinstance(b.coordinator, GateCoordinator)

    def test_mocks_empty_by_default(self) -> None:
        """
        mocks — пустой словарь. Действия без зависимостей
        работают без дополнительной настройки.
        """
        # Arrange & Act
        b = TestBench()

        # Assert
        assert b.mocks == {}

    def test_plugins_empty_by_default(self) -> None:
        """
        plugins — пустой список. Плагины подключаются явно
        при необходимости.
        """
        # Arrange & Act
        b = TestBench()

        # Assert
        assert b.plugins == []


class TestWithMocks:
    """TestBench корректно сохраняет переданные моки."""

    def test_regular_object_stored_as_is(self) -> None:
        """
        Обычный объект (PaymentService) сохраняется как есть.

        PaymentService — не Mock, не BaseAction, не BaseResult.
        По правилам _prepare_mock: обычный объект → как есть (для box.resolve()).
        Аспект вызывает payment.charge() напрямую.
        """
        # Arrange
        payment = PaymentService()

        # Act
        b = TestBench(mocks={PaymentService: payment})

        # Assert
        assert b._prepared_mocks[PaymentService] is payment

    def test_async_mock_stored_as_is(self) -> None:
        """
        AsyncMock(spec=PaymentService) сохраняется как есть.

        AsyncMock является callable, но НЕ должен оборачиваться
        в MockAction. Правило 3 (_prepare_mock) проверяет isinstance(Mock)
        ПЕРЕД callable и возвращает мок как есть.
        """
        # Arrange
        mock = AsyncMock(spec=PaymentService)

        # Act
        b = TestBench(mocks={PaymentService: mock})

        # Assert — мок передан как есть, не обёрнут в MockAction
        assert b._prepared_mocks[PaymentService] is mock
