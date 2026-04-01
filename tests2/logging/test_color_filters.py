# tests2/logging/test_color_filters.py
"""
Тесты цветовых фильтров в шаблонах логирования.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет обработку цветовых фильтров в шаблонах логирования. Цвета задаются
двумя способами:

1. Фильтр после переменной: {%var.text|red}
2. Цветовая функция внутри iif: red('text')

Цвета могут быть простыми (foreground), с префиксом bg_ (background),
или комбинированными (foreground_on_background). Поддерживаются 8 основных
цветов и их bright-варианты.

VariableSubstitutor преобразует цветовые маркеры в ANSI-коды на последнем этапе.
Этот файл тестирует полный цикл: от шаблона до ANSI-строки.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Простой foreground цвет (red, green, blue и т.д.).
- Background цвет (bg_red, bg_blue).
- Комбинированный цвет (red_on_blue, green_on_black).
- Bright-варианты (orange, bright_green, bg_bright_red).
- Цветовая функция внутри iif.
- Ошибки при неизвестном цвете.
- Ошибки при некорректном формате имени цвета.
- Обработка нескольких цветов в одном сообщении.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor


@pytest.fixture
def substitutor() -> VariableSubstitutor:
    """Экземпляр подстановщика переменных."""
    return VariableSubstitutor()


@pytest.fixture
def empty_context() -> Context:
    """Пустой контекст."""
    return Context()


@pytest.fixture
def empty_scope() -> LogScope:
    """Пустой scope."""
    return LogScope()


@pytest.fixture
def empty_state() -> BaseState:
    """Пустое состояние."""
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    """Пустые параметры."""
    return BaseParams()


# ======================================================================
# ТЕСТЫ: Цветовые фильтры (|color)
# ======================================================================


class TestColorFilters:
    """Тесты цветовых фильтров в шаблонах."""

    def test_foreground_color(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        {%var.text|red} → ANSI-код для красного цвета.
        """
        result = substitutor.substitute(
            "{%var.text|red}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[31mhello\033[0m" in result

    def test_background_color(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        {%var.text|bg_red} → красный фон.
        """
        result = substitutor.substitute(
            "{%var.text|bg_red}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[41mhello\033[0m" in result

    def test_foreground_on_background(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        {%var.text|red_on_blue} → красный текст на синем фоне.
        """
        result = substitutor.substitute(
            "{%var.text|red_on_blue}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[31;44mhello\033[0m" in result

    def test_bright_colors(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Bright-цвета: orange (91), bright_blue (94) и т.д.
        """
        result = substitutor.substitute(
            "{%var.text|orange_on_bright_blue}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        # orange = 91, bright_blue background = 104
        assert "\033[91;104mhello\033[0m" in result

    def test_multiple_colors_in_one_message(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Несколько цветовых фильтров в одном сообщении.
        """
        result = substitutor.substitute(
            "{%var.a|red} and {%var.b|green}",
            {"a": "red", "b": "green"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[31mred\033[0m" in result
        assert "\033[32mgreen\033[0m" in result

    def test_unknown_foreground_color_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Неизвестный цвет → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_unknown_foreground_in_combination_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Неизвестный foreground в комбинации → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown foreground color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink_on_blue}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_unknown_background_in_combination_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Неизвестный background в комбинации → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown background color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|red_on_hotpink}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_malformed_color_name_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Имя цвета с несколькими '_on_' (red_on_blue_on_green) →
        часть после первого '_on_' трактуется как background,
        если background не найден → ошибка.
        """
        with pytest.raises(LogTemplateError, match="Unknown background color: 'blue_on_green'"):
            substitutor.substitute(
                "{%var.text|red_on_blue_on_green}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )


# ======================================================================
# ТЕСТЫ: Цветовые функции внутри iif
# ======================================================================


class TestColorFunctionsInIif:
    """Цветовые функции (red('text')) внутри iif."""

    def test_color_function_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        {iif(1 > 0; red('yes'); green('no'))} → красное 'yes'.
        """
        result = substitutor.substitute(
            "{iif(1 > 0; red('yes'); green('no'))}",
            {},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[31myes\033[0m" in result
        assert "green" not in result

    def test_color_function_with_variable_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Переменная внутри iif, переданная в цветовую функцию.
        """
        result = substitutor.substitute(
            "{iif({%var.ok}; green('OK'); red('FAIL'))}",
            {"ok": True},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[32mOK\033[0m" in result

    def test_nested_color_functions(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Вложенные цветовые функции внутри iif.
        """
        result = substitutor.substitute(
            "{iif(1 > 0; red('level: ' + green('ok')); 'no')}",
            {},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[31mlevel: \033[0m" in result
        assert "\033[32mok\033[0m" in result


# ======================================================================
# ТЕСТЫ: Комбинирование цветовых фильтров и функций
# ======================================================================


class TestCombined:
    """Смешанное использование фильтров и функций."""

    def test_color_filter_and_function_together(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """
        Цветовой фильтр вне iif и цветовая функция внутри iif.
        """
        result = substitutor.substitute(
            "Static: {%var.static|blue} and {iif(1 > 0; red('dynamic'); '')}",
            {"static": "blue"},
            empty_scope, empty_context, empty_state, empty_params,
        )
        assert "\033[34mblue\033[0m" in result
        assert "\033[31mdynamic\033[0m" in result