# tests/naming/test_naming_suffixes.py
"""
Тесты инвариантов именования компонентов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что все компоненты ActionMachine соблюдают обязательные суффиксы
и префиксы в именах. Инварианты именования обнаруживаются как можно раньше:
- Суффиксы классов проверяются в __init_subclass__ при определении класса.
- Суффиксы методов проверяются при применении декоратора.
- Префиксы методов проверяются при применении декоратора.

Правильный суффикс/префикс → регистрация/декорирование проходит.
Неправильный → NamingSuffixError / NamingPrefixError.

Все сломанные классы и методы создаются внутри тестов, потому что они
заведомо не могут быть частью рабочей доменной модели.

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

    Класс Action (наследник BaseAction)          → суффикс "Action"
    Класс Domain (наследник BaseDomain)           → суффикс "Domain"
    Класс Checker (наследник ResultFieldChecker)  → суффикс "Checker"
    Метод с @regular_aspect                       → суффикс "_aspect"
    Метод с @summary_aspect                       → суффикс "_summary"
    Метод с @on_error                             → суффикс "_on_error"
    Метод плагина с @on                           → префикс "on_"
"""

import pytest

from action_machine.core.exceptions import NamingPrefixError, NamingSuffixError

# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "Action" для BaseAction
# ═════════════════════════════════════════════════════════════════════════════


class TestActionSuffix:
    """Каждый класс, наследующий BaseAction, обязан заканчиваться на 'Action'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'MyTaskAction' → определение класса проходит без ошибок."""

        # Arrange & Act — определяем класс с правильным суффиксом
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult

        class MyTaskAction(BaseAction[BaseParams, BaseResult]):
            pass

        # Assert — класс определился успешно
        assert MyTaskAction.__name__.endswith("Action")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'MyTask' без суффикса 'Action' → NamingSuffixError."""

        # Arrange & Act & Assert — определение класса выбрасывает ошибку
        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTask(BaseAction[BaseParams, BaseResult]):
                pass

    def test_wrong_suffix_raises(self) -> None:
        """Имя 'MyTaskHandler' → NamingSuffixError (суффикс не 'Action')."""

        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTaskHandler(BaseAction[BaseParams, BaseResult]):
                pass

    def test_indirect_subclass_checked(self) -> None:
        """Косвенный наследник BaseAction без суффикса → NamingSuffixError."""

        from action_machine.core.base_action import BaseAction
        from action_machine.core.base_params import BaseParams
        from action_machine.core.base_result import BaseResult

        # Промежуточный класс с правильным суффиксом
        class BaseTaskAction(BaseAction[BaseParams, BaseResult]):
            pass

        # Косвенный наследник без суффикса
        with pytest.raises(NamingSuffixError, match="Action"):
            class SpecificTask(BaseTaskAction):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "Domain" для BaseDomain
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainSuffix:
    """Каждый класс, наследующий BaseDomain, обязан заканчиваться на 'Domain'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'ShippingDomain' → определение проходит."""

        from action_machine.domain.base_domain import BaseDomain

        class ShippingDomain(BaseDomain):
            name = "shipping"
            description = "Домен доставки"

        assert ShippingDomain.__name__.endswith("Domain")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'Shipping' без суффикса 'Domain' → NamingSuffixError."""

        from action_machine.domain.base_domain import BaseDomain

        with pytest.raises(NamingSuffixError, match="Domain"):
            class Shipping(BaseDomain):
                name = "shipping"
                description = "Домен доставки без суффикса"

    def test_intermediate_without_name_still_needs_suffix(self) -> None:
        """Промежуточный абстрактный домен без name, но с правильным суффиксом → OK."""

        from action_machine.domain.base_domain import BaseDomain

        # Промежуточный класс без name — допускается, но суффикс обязателен
        class ExternalServiceDomain(BaseDomain):
            name = "external_service"
            description = "Внешний сервис"
            is_external = True

        assert ExternalServiceDomain.__name__.endswith("Domain")

    def test_intermediate_without_suffix_raises(self) -> None:
        """Промежуточный абстрактный домен без суффикса → NamingSuffixError."""

        from action_machine.domain.base_domain import BaseDomain

        with pytest.raises(NamingSuffixError, match="Domain"):
            class ExternalService(BaseDomain):
                description = "Внешний сервис без суффикса"
                is_external = True


# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "Checker" для ResultFieldChecker
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckerSuffix:
    """Каждый класс, наследующий ResultFieldChecker, обязан заканчиваться на 'Checker'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'ResultEmailChecker' → определение проходит."""

        from action_machine.checkers.result_field_checker import ResultFieldChecker

        class ResultEmailChecker(ResultFieldChecker):
            def _check_type_and_constraints(self, value):
                pass

        assert ResultEmailChecker.__name__.endswith("Checker")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'EmailValidator' без суффикса 'Checker' → NamingSuffixError."""

        from action_machine.checkers.result_field_checker import ResultFieldChecker

        with pytest.raises(NamingSuffixError, match="Checker"):
            class EmailValidator(ResultFieldChecker):
                def _check_type_and_constraints(self, value):
                    pass

    def test_existing_checkers_have_suffix(self) -> None:
        """Все встроенные чекеры имеют суффикс 'Checker'."""

        from action_machine.checkers import (
            ResultBoolChecker,
            ResultDateChecker,
            ResultFloatChecker,
            ResultInstanceChecker,
            ResultIntChecker,
            ResultStringChecker,
        )

        for checker_cls in [
            ResultBoolChecker, ResultDateChecker, ResultFloatChecker,
            ResultInstanceChecker, ResultIntChecker, ResultStringChecker,
        ]:
            assert checker_cls.__name__.endswith("Checker"), (
                f"{checker_cls.__name__} не заканчивается на 'Checker'"
            )


# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "_aspect" для @regular_aspect
# ═════════════════════════════════════════════════════════════════════════════


class TestRegularAspectSuffix:
    """Метод с @regular_aspect обязан заканчиваться на '_aspect'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'validate_data_aspect' → декоратор применяется без ошибок."""

        from action_machine.aspects.regular_aspect import regular_aspect

        @regular_aspect("Валидация данных")
        async def validate_data_aspect(self, params, state, box, connections):
            return {}

        assert hasattr(validate_data_aspect, "_new_aspect_meta")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'validate_data' без '_aspect' → NamingSuffixError."""

        from action_machine.aspects.regular_aspect import regular_aspect

        with pytest.raises(NamingSuffixError, match="_aspect"):
            @regular_aspect("Валидация данных")
            async def validate_data(self, params, state, box, connections):
                return {}

    def test_wrong_suffix_raises(self) -> None:
        """Имя 'validate_data_step' → NamingSuffixError."""

        from action_machine.aspects.regular_aspect import regular_aspect

        with pytest.raises(NamingSuffixError, match="_aspect"):
            @regular_aspect("Валидация данных")
            async def validate_data_step(self, params, state, box, connections):
                return {}


# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "_summary" для @summary_aspect
# ═════════════════════════════════════════════════════════════════════════════


class TestSummaryAspectSuffix:
    """Метод с @summary_aspect обязан заканчиваться на '_summary' или называться 'summary'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'build_result_summary' → декоратор применяется без ошибок."""

        from action_machine.aspects.summary_aspect import summary_aspect

        @summary_aspect("Формирование результата")
        async def build_result_summary(self, params, state, box, connections):
            pass

        assert hasattr(build_result_summary, "_new_aspect_meta")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'build_result' без '_summary' → NamingSuffixError."""

        from action_machine.aspects.summary_aspect import summary_aspect

        with pytest.raises(NamingSuffixError, match="_summary"):
            @summary_aspect("Формирование результата")
            async def build_result(self, params, state, box, connections):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Суффикс "_on_error" для @on_error
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorSuffix:
    """Метод с @on_error обязан заканчиваться на '_on_error'."""

    def test_correct_suffix_passes(self) -> None:
        """Имя 'handle_validation_on_error' → декоратор применяется."""

        from action_machine.on_error import on_error

        @on_error(ValueError, description="Ошибка валидации")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            pass

        assert hasattr(handle_validation_on_error, "_on_error_meta")

    def test_missing_suffix_raises(self) -> None:
        """Имя 'handle_validation' без '_on_error' → NamingSuffixError."""

        from action_machine.on_error import on_error

        with pytest.raises(NamingSuffixError, match="_on_error"):
            @on_error(ValueError, description="Ошибка валидации")
            async def handle_validation(self, params, state, box, connections, error):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Префикс "on_" для @on (плагины)
# ═════════════════════════════════════════════════════════════════════════════

class TestPluginOnPrefix:
    """Метод плагина с @on обязан начинаться с 'on_'."""

    def test_correct_prefix_passes(self) -> None:
        """Имя 'on_track_finish' → декоратор применяется."""
        from action_machine.plugins.decorators import on
        from action_machine.plugins.events import GlobalFinishEvent

        @on(GlobalFinishEvent)
        async def on_track_finish(self, state, event, log):
            return state

        assert hasattr(on_track_finish, "_on_subscriptions")

    def test_missing_prefix_raises(self) -> None:
        """Имя 'track_finish' без 'on_' → NamingPrefixError."""
        from action_machine.plugins.decorators import on
        from action_machine.plugins.events import GlobalFinishEvent

        with pytest.raises(NamingPrefixError, match="on_"):
            @on(GlobalFinishEvent)
            async def track_finish(self, state, event, log):
                return state

    def test_wrong_prefix_raises(self) -> None:
        """Имя 'handle_track_finish' → NamingPrefixError (не начинается с 'on_')."""
        from action_machine.plugins.decorators import on
        from action_machine.plugins.events import GlobalFinishEvent

        with pytest.raises(NamingPrefixError, match="on_"):
            @on(GlobalFinishEvent)
            async def handle_track_finish(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# Обязательность description (не пустая строка)
# ═════════════════════════════════════════════════════════════════════════════


class TestDescriptionRequired:
    """Description обязателен и не может быть пустой строкой для всех декораторов."""

    def test_regular_aspect_empty_description_raises(self) -> None:
        """@regular_aspect("") → ValueError."""

        from action_machine.aspects.regular_aspect import regular_aspect

        with pytest.raises(ValueError, match="не может быть пустой"):
            @regular_aspect("")
            async def validate_aspect(self, params, state, box, connections):
                return {}

    def test_summary_aspect_empty_description_raises(self) -> None:
        """@summary_aspect("") → ValueError."""

        from action_machine.aspects.summary_aspect import summary_aspect

        with pytest.raises(ValueError, match="не может быть пустой"):
            @summary_aspect("")
            async def result_summary(self, params, state, box, connections):
                pass

    def test_on_error_empty_description_raises(self) -> None:
        """@on_error(ValueError, description="") → ValueError."""

        from action_machine.on_error import on_error

        with pytest.raises(ValueError, match="не может быть пустой"):
            on_error(ValueError, description="")

    def test_regular_aspect_whitespace_description_raises(self) -> None:
        """@regular_aspect("   ") → ValueError."""

        from action_machine.aspects.regular_aspect import regular_aspect

        with pytest.raises(ValueError, match="не может быть пустой"):
            @regular_aspect("   ")
            async def validate_aspect(self, params, state, box, connections):
                return {}
