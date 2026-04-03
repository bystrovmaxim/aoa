# tests/on_error/test_on_error_validation.py
"""
Тесты валидации обработчиков @on_error при сборке метаданных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет валидацию порядка обработчиков и перекрытия типов:
- Общий обработчик выше специфичного → TypeError при сборке.
- Одинаковые типы в двух обработчиках → TypeError при сборке.
- Подкласс вышестоящего типа → TypeError при сборке.
- Допустимый порядок (специфичный → общий) → сборка проходит.
- Обработчик без OnErrorGateHost → TypeError при сборке.

Все тесты создают намеренно сломанные классы внутри тестов, потому что
они не могут быть частью рабочей доменной модели.
"""

import pytest

from action_machine.metadata import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Перекрытие типов (общий выше специфичного)
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorOverlapValidation:
    """Тесты перекрытия типов между обработчиками @on_error."""

    def test_general_above_specific_raises(self) -> None:
        """Exception выше ValueError → TypeError: ValueError перекрыт Exception."""

        # Arrange — определяем Action с неправильным порядком обработчиков.
        # Exception ловит всё, ValueError никогда не получит управления.

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain import OrdersDomain

        @meta(description="Неправильный порядок обработчиков", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class BadOrderAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(Exception, description="Общий — перехватит всё")
            async def general_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ValueError, description="Специфичный — мёртвый код")
            async def specific_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert — MetadataBuilder обнаруживает перекрытие
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(BadOrderAction)

    def test_same_type_in_two_handlers_raises(self) -> None:
        """Один и тот же тип в двух обработчиках → TypeError."""

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain import OrdersDomain

        @meta(description="Два обработчика на один тип", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class DuplicateHandlerAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="Первый обработчик ValueError")
            async def first_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ValueError, description="Второй обработчик ValueError — дубль")
            async def second_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(DuplicateHandlerAction)

    def test_subclass_covered_by_parent_raises(self) -> None:
        """Вышестоящий ловит родительский тип, нижестоящий — дочерний → TypeError."""

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
        from tests.domain import OrdersDomain

        @meta(description="Родитель перекрывает дочерний", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class ParentCoversChildAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ParentError, description="Ловит ParentError и всех наследников")
            async def parent_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(ChildError, description="ChildError — мёртвый код")
            async def child_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act & Assert — ChildError подкласс ParentError → перекрытие
        with pytest.raises(TypeError, match="перехватывает"):
            MetadataBuilder.build(ParentCoversChildAction)


# ═════════════════════════════════════════════════════════════════════════════
# Допустимый порядок (специфичный → общий)
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorValidOrder:
    """Допустимый порядок обработчиков — сборка проходит без ошибок."""

    def test_specific_above_general_ok(self) -> None:
        """ValueError выше Exception → допустимо, сборка проходит."""

        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain import OrdersDomain

        @meta(description="Правильный порядок обработчиков", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class CorrectOrderAction(BaseAction[BaseParams, BaseResult]):

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="Специфичный — первый")
            async def specific_on_error(self, params, state, box, connections, error):
                return BaseResult()

            @on_error(Exception, description="Общий fallback — последний")
            async def general_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act — сборка проходит без ошибок
        metadata = MetadataBuilder.build(CorrectOrderAction)

        # Assert — оба обработчика собраны
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
        from tests.domain import OrdersDomain

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

        from tests.domain import ErrorHandledAction

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

        from tests.domain import MultiErrorAction
        from tests.domain.error_actions import InsufficientFundsError, PaymentGatewayError

        # Act
        metadata = MetadataBuilder.build(MultiErrorAction)

        # Assert — три обработчика в правильном порядке
        assert len(metadata.error_handlers) == 3
        assert metadata.error_handlers[0].exception_types == (InsufficientFundsError,)
        assert metadata.error_handlers[1].exception_types == (PaymentGatewayError,)
        assert metadata.error_handlers[2].exception_types == (Exception,)

    def test_no_handlers_collected(self) -> None:
        """Действие без @on_error → error_handlers пустой."""

        from tests.domain import NoErrorHandlerAction

        # Act
        metadata = MetadataBuilder.build(NoErrorHandlerAction)

        # Assert
        assert not metadata.has_error_handlers()
        assert len(metadata.error_handlers) == 0
