# tests/on_error/test_on_error_validation.py
"""
Tests for validation of @on_error handlers during metadata build.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verifies validation of handler order and type overlaps:
- General handler above specific → TypeError on build.
- Same types in two handlers → TypeError on build.
- Subclass covered by parent type → TypeError on build.
- Valid order (specific → general) → build passes.
- Handler without OnErrorGateHost → TypeError on build.

All tests create intentionally broken classes inside tests, because
they cannot be part of the working domain model.
"""

import pytest

from action_machine.metadata import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Type overlaps (general above specific)
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorOverlapValidation:
    """Tests for type overlaps between @on_error handlers."""

    def test_general_above_specific_raises(self) -> None:
        """Exception above ValueError → TypeError: ValueError covered by Exception."""

        # Arrange — define Action with wrong handler order.
        # Exception catches everything, ValueError never gets control.

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain_model import OrdersDomain

        @meta(description="Wrong handler order", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class BadOrderAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(Exception, description="General — catches everything")
            async def general_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ValueError, description="Specific — dead code")
            async def specific_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert — MetadataBuilder detects overlap
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(BadOrderAction)

    def test_same_type_in_two_handlers_raises(self) -> None:
        """Same type in two handlers → TypeError."""

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain_model import OrdersDomain

        @meta(description="Two handlers for one type", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class DuplicateHandlerAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="First ValueError handler")
            async def first_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ValueError, description="Second ValueError handler — duplicate")
            async def second_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(DuplicateHandlerAction)

    def test_subclass_covered_by_parent_raises(self) -> None:
        """Parent catches parent type, child catches child → TypeError."""

        class ParentError(Exception):
            pass

        class ChildError(ParentError):
            pass

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain_model import OrdersDomain

        @meta(description="Parent covers child", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class ParentCoversChildAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ParentError, description="Catches ParentError and all subclasses")
            async def parent_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ChildError, description="ChildError — dead code")
            async def child_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert — ChildError is subclass of ParentError → overlap
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(ParentCoversChildAction)


# ═════════════════════════════════════════════════════════════════════════════
# Valid order (specific → general)
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorValidOrder:
    """Valid handler order — build passes without errors."""

    def test_specific_above_general_ok(self) -> None:
        """ValueError above Exception → valid, build passes."""

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain_model import OrdersDomain

        @meta(description="Correct handler order", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class CorrectOrderAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="Specific — first")
            async def specific_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(Exception, description="General fallback — last")
            async def general_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act — build passes without errors
        metadata = MetadataBuilder.build(CorrectOrderAction)

        # Assert — both handlers collected
        assert len(metadata.error_handlers) == 2
        assert metadata.error_handlers[0].method_name == "specific_on_error"
        assert metadata.error_handlers[1].method_name == "general_on_error"

    def test_unrelated_types_ok(self) -> None:
        """Два обработчика с несвязанными типами → допустимо."""

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain_model import OrdersDomain

        @meta(description="Несвязанные типы", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class UnrelatedTypesAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="ValueError")
            async def value_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(TypeError, description="TypeError")
            async def type_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act — сборка проходит без ошибок
        metadata = MetadataBuilder.build(UnrelatedTypesAction)

        # Assert
        assert len(metadata.error_handlers) == 2


# ═════════════════════════════════════════════════════════════════════════════
# Гейтхост OnErrorGateHost
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorGateHostValidation:
    """Класс без OnErrorGateHost с @on_error → TypeError при сборке."""

    def test_on_error_without_gate_host_raises(self) -> None:
        """@on_error на классе без OnErrorGateHost → TypeError."""

        # Arrange — класс не наследует BaseAction (и, следовательно,
        # OnErrorGateHost), но содержит метод с @on_error.
        # Такой класс — намеренно сломанный для edge-case теста.

        from action_machine.on_error import on_error

        class NotAnAction:
            @on_error(ValueError, description="Обработка")
            async def handle_on_error(self, params, state, box, connections, error):
                pass

        # Act & Assert — MetadataBuilder обнаруживает отсутствие гейтхоста
        with pytest.raises(TypeError, match="OnErrorGateHost"):
            MetadataBuilder.build(NotAnAction)


# ═════════════════════════════════════════════════════════════════════════════
# Один обработчик — сборка метаданных корректна
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorMetadataCollection:
    """Проверяет корректность сборки метаданных @on_error."""

    def test_single_handler_collected(self) -> None:
        """Один обработчик → собирается в metadata.error_handlers."""

        from tests.domain_model import ErrorHandledAction

        # Act
        metadata = MetadataBuilder.build(ErrorHandledAction)

        # Assert
        assert metadata.has_error_handlers()
        assert len(metadata.error_handlers) == 1
        handler = metadata.error_handlers[0]
        assert handler.method_name == "handle_validation_on_error"
        assert handler.exception_types == (ValueError,)
        assert handler.description == "Обработка ошибки валидации"

    def test_multiple_handlers_collected_in_order(self) -> None:
        """Несколько обработчиков → собираются в порядке объявления."""

        from tests.domain_model import MultiErrorAction
        from tests.domain_model.error_actions import InsufficientFundsError, PaymentGatewayError

        # Act
        metadata = MetadataBuilder.build(MultiErrorAction)

        # Assert — три обработчика в правильном порядке
        assert len(metadata.error_handlers) == 3
        assert metadata.error_handlers[0].exception_types == (InsufficientFundsError,)
        assert metadata.error_handlers[1].exception_types == (PaymentGatewayError,)
        assert metadata.error_handlers[2].exception_types == (Exception,)

    def test_no_handlers_collected(self) -> None:
        """Действие без @on_error → error_handlers пустой."""

        from tests.domain_model import NoErrorHandlerAction

        # Act
        metadata = MetadataBuilder.build(NoErrorHandlerAction)

        # Assert
        assert not metadata.has_error_handlers()
        assert len(metadata.error_handlers) == 0
