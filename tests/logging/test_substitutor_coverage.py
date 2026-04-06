# tests/logging/test_substitutor_coverage.py
"""
Целевые тесты покрытия для VariableSubstitutor.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Закрывает непокрытые строки в variable_substitutor.py [4]:

- Навигация по BaseSchema через DotPathNavigator [2].
- Навигация по обычному dict (ключ не найден).
- Навигация через getattr для произвольных объектов.
- _get_property_config — обнаружение @sensitive [1].
- _quote_if_string — форматирование цветовых маркеров.
- _format_variable_for_template — inside_iif ветки
  для bool, int, string.
- _substitute_with_iif_detection — переменные
  внутри и вне блоков iif одновременно.
- _substitute_variables — диспетчер быстрого/медленного пути.
- _resolve_color_name — ветка bg_ (только фон).
- _resolve_color_name — ветка fg_on_bg (foreground + background).

═══════════════════════════════════════════════════════════════════════════════
ОРГАНИЗАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- TestQuoteIfString — статический метод _quote_if_string для всех типов.
- TestResolveColorName — все три формата имени цвета и ошибки.
- TestIifWithMixedVariables — шаблоны с переменными одновременно внутри
  и вне {iif(...)}.
- TestNamespaceResolution — state, params, context namespace.
- TestDebugInsideIifTemplate — debug-фильтр рядом с iif.
- TestNavigationSteps — навигация через DotPathNavigator для BaseSchema,
  dict, произвольных объектов.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor
from action_machine.testing.stubs import ContextStub
from tests.domain import SimpleAction


# ─────────────────────────────────────────────────────────────────────────────
# Общие фикстуры
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sub() -> VariableSubstitutor:
    """Свежий экземпляр VariableSubstitutor."""
    return VariableSubstitutor()


@pytest.fixture()
def scope() -> LogScope:
    """Минимальный LogScope для тестов подстановки."""
    return LogScope(machine="M", mode="test", action="A", aspect="a", nest_level=0)


@pytest.fixture()
def ctx() -> Context:
    """Минимальный Context для тестов подстановки."""
    return Context()


@pytest.fixture()
def state() -> BaseState:
    """Пустой BaseState для тестов подстановки."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Пустой BaseParams для тестов подстановки."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
# _quote_if_string — форматирование литералов для simpleeval
# ═════════════════════════════════════════════════════════════════════════════

class TestQuoteIfString:
    """Покрывает _quote_if_string для всех типов значений."""

    def test_boolean_true_not_quoted(self) -> None:
        """True возвращается как строка 'True' без кавычек."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(True)

        # Assert — булевы значения не оборачиваются в кавычки
        assert result == "True"

    def test_boolean_false_not_quoted(self) -> None:
        """False возвращается как строка 'False' без кавычек."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(False)

        # Assert
        assert result == "False"

    def test_integer_not_quoted(self) -> None:
        """Целое число возвращается как строка без кавычек."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(42)

        # Assert
        assert result == "42"

    def test_float_not_quoted(self) -> None:
        """Дробное число возвращается как строка без кавычек."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(3.14)

        # Assert
        assert result == "3.14"

    def test_plain_string_quoted(self) -> None:
        """Обычная строка оборачивается в одинарные кавычки."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string("hello")

        # Assert
        assert result == "'hello'"

    def test_string_with_single_quote_escaped(self) -> None:
        """Строка с одинарной кавычкой внутри — кавычка экранируется."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string("it's")

        # Assert — внутренняя кавычка экранирована
        assert "\\'" in result

    def test_color_marker_not_quoted(self) -> None:
        """Цветовой маркер возвращается без кавычек для сохранения маркера."""
        # Arrange — строка содержит __COLOR(...)...__COLOR_END__
        marker = "__COLOR(red)error__COLOR_END__"

        # Act
        result = VariableSubstitutor._quote_if_string(marker)

        # Assert — маркер возвращён как есть, без обёртки в кавычки
        assert result == marker


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_color_name — все три формата имени цвета
# ═════════════════════════════════════════════════════════════════════════════

class TestResolveColorName:
    """Покрывает _resolve_color_name: fg, bg_, fg_on_bg и ошибки."""

    def test_simple_foreground(self, sub) -> None:
        """Простое имя цвета возвращает foreground ANSI-код."""
        # Arrange / Act
        result = sub._resolve_color_name("green")

        # Assert — green = ANSI код 32
        assert result == "\033[32m"

    def test_background_color(self, sub) -> None:
        """Имя с префиксом bg_ возвращает background ANSI-код."""
        # Arrange / Act
        result = sub._resolve_color_name("bg_red")

        # Assert — bg_red = ANSI код 41
        assert result == "\033[41m"

    def test_foreground_on_background(self, sub) -> None:
        """Формат fg_on_bg возвращает комбинированный ANSI-код."""
        # Arrange / Act
        result = sub._resolve_color_name("red_on_blue")

        # Assert — red=31, blue=44
        assert result == "\033[31;44m"

    def test_unknown_foreground_raises(self, sub) -> None:
        """Неизвестное имя foreground вызывает LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="color"):
            sub._resolve_color_name("rainbow")

    def test_unknown_background_alone_raises(self, sub) -> None:
        """Неизвестное имя bg_ вызывает LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("bg_rainbow")

    def test_unknown_fg_in_combo_raises(self, sub) -> None:
        """Неизвестный foreground в fg_on_bg вызывает LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="foreground"):
            sub._resolve_color_name("fakefg_on_blue")

    def test_unknown_bg_in_combo_raises(self, sub) -> None:
        """Неизвестный background в fg_on_bg вызывает LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("red_on_fakebg")


# ═════════════════════════════════════════════════════════════════════════════
# Переменные одновременно внутри и вне {iif(...)}
# ═════════════════════════════════════════════════════════════════════════════

class TestIifWithMixedVariables:
    """Покрывает _substitute_with_iif_detection — медленный путь."""

    def test_var_outside_and_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Переменная вне iif — plain string, внутри iif — литерал."""
        # Arrange — шаблон содержит {%var.label} снаружи и {%var.x} внутри iif
        template = "Label: {%var.label} Result: {iif({%var.x} > 0; 'pos'; 'neg')}"

        # Act
        result = sub.substitute(template, {"label": "test", "x": 5}, scope, ctx, state, params)

        # Assert — обе подстановки выполнены корректно
        assert "Label: test" in result
        assert "pos" in result

    def test_boolean_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Булева переменная внутри iif форматируется без кавычек."""
        # Arrange — flag=True → подставляется как True (без кавычек)
        template = "{iif({%var.flag}; 'yes'; 'no')}"

        # Act
        result = sub.substitute(template, {"flag": True}, scope, ctx, state, params)

        # Assert
        assert "yes" in result

    def test_integer_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Целочисленная переменная внутри iif форматируется без кавычек."""
        # Arrange — count=3 → подставляется как 3 (число, не строка '3')
        template = "{iif({%var.count} > 0; 'some'; 'none')}"

        # Act
        result = sub.substitute(template, {"count": 3}, scope, ctx, state, params)

        # Assert
        assert "some" in result

    def test_string_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Строковая переменная внутри iif оборачивается в кавычки."""
        # Arrange — status='ok' → подставляется как 'ok' (с кавычками)
        template = "{iif({%var.status} == 'ok'; 'good'; 'bad')}"

        # Act
        result = sub.substitute(template, {"status": "ok"}, scope, ctx, state, params)

        # Assert
        assert "good" in result

    def test_multiple_vars_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Несколько переменных внутри одного iif."""
        # Arrange — обе переменные внутри iif
        template = "{iif({%var.x} + {%var.y} > 10; 'big'; 'small')}"

        # Act
        result = sub.substitute(template, {"x": 7, "y": 5}, scope, ctx, state, params)

        # Assert
        assert "big" in result


# ═════════════════════════════════════════════════════════════════════════════
# Разрешение namespace: state, params, context
# ═════════════════════════════════════════════════════════════════════════════

class TestNamespaceResolution:
    """Покрывает резольверы для state, params, context namespace."""

    def test_state_variable(self, sub, scope, ctx, params) -> None:
        """Namespace state разрешает значения из BaseState."""
        # Arrange — state содержит txn_id
        st = BaseState(txn_id="TXN-001")

        # Act
        result = sub.substitute("{%state.txn_id}", {}, scope, ctx, st, params)

        # Assert
        assert "TXN-001" in result

    def test_params_variable(self, sub, scope, ctx, state) -> None:
        """Namespace params разрешает значения из полей Params."""
        # Arrange — SimpleAction.Params имеет поле name
        p = SimpleAction.Params(name="Alice")

        # Act
        result = sub.substitute("{%params.name}", {}, scope, ctx, state, p)

        # Assert
        assert "Alice" in result

    def test_context_nested_variable(self, sub, scope, state, params) -> None:
        """Namespace context разрешает вложенные поля через dot-path."""
        # Arrange — ContextStub содержит user.user_id
        c = ContextStub()

        # Act
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)

        # Assert
        assert "test_user" in result

    def test_scope_nested_variable(self, sub, ctx, state, params) -> None:
        """Namespace scope разрешает поля LogScope [3]."""
        # Arrange — LogScope содержит action
        sc = LogScope(machine="M", mode="test", action="MyAction", aspect="a", nest_level=0)

        # Act
        result = sub.substitute("{%scope.action}", {}, sc, ctx, state, params)

        # Assert
        assert "MyAction" in result


# ═════════════════════════════════════════════════════════════════════════════
# Debug-фильтр рядом с iif в одном шаблоне
# ═════════════════════════════════════════════════════════════════════════════

class TestDebugInsideIifTemplate:
    """Покрывает шаблон с |debug и {iif(...)} одновременно."""

    def test_debug_and_iif_together(self, sub, scope, ctx, state, params) -> None:
        """Debug-фильтр и iif в одном шаблоне оба корректно обрабатываются."""
        # Arrange — |debug вне iif, {iif} с числовым условием
        template = "{%var.obj|debug} - {iif({%var.x} > 0; 'ok'; 'fail')}"

        # Act
        result = sub.substitute(
            template,
            {"obj": {"key": "val"}, "x": 1},
            scope, ctx, state, params,
        )

        # Assert — debug вывел содержимое объекта, iif вернул 'ok'
        assert "key" in result
        assert "ok" in result


# ═════════════════════════════════════════════════════════════════════════════
# Навигация — DotPathNavigator для разных типов объектов
# ═════════════════════════════════════════════════════════════════════════════

class TestNavigationSteps:
    """Покрывает навигацию через DotPathNavigator для BaseSchema, dict, generic."""

    def test_dict_navigation(self, sub, scope, ctx, state, params) -> None:
        """Навигация по вложенному dict через dot-path."""
        # Arrange — трёхуровневый вложенный dict
        template = "{%var.a.b.c}"
        var = {"a": {"b": {"c": "deep"}}}

        # Act
        result = sub.substitute(template, var, scope, ctx, state, params)

        # Assert
        assert "deep" in result

    def test_object_navigation_via_getattr(self, sub, scope, ctx, state, params) -> None:
        """Навигация по атрибутам объекта через getattr."""
        # Arrange — context.user является объектом с атрибутом user_id
        c = ContextStub()

        # Act
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)

        # Assert
        assert "test_user" in result

    def test_state_navigation(self, sub, scope, ctx, params) -> None:
        """Навигация по BaseState (BaseSchema) через __getitem__ [2]."""
        # Arrange — BaseState поддерживает __getitem__
        st = BaseState(nested={"key": "value"})

        # Act
        result = sub.substitute("{%state.nested.key}", {}, scope, ctx, st, params)

        # Assert
        assert "value" in result

    def test_missing_intermediate_key(self, sub, scope, ctx, state, params) -> None:
        """Отсутствующий промежуточный ключ в dot-path → LogTemplateError."""
        # Arrange — var.a существует, но var.a.missing — нет
        template = "{%var.a.missing.deep}"

        # Act / Assert
        with pytest.raises(LogTemplateError):
            sub.substitute(template, {"a": {"other": 1}}, scope, ctx, state, params)