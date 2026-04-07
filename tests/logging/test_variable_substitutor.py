# tests/logging/test_variable_substitutor.py
"""
Полные тесты VariableSubstitutor — движка подстановки переменных в шаблонах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Покрывает все аспекты работы VariableSubstitutor [4]:

- Разрешение переменных из пяти namespace: var, state, scope, context, params.
- Навигация по вложенным объектам через DotPathNavigator.
- Защита от доступа к приватным атрибутам (проверка '_' во всех сегментах).
- Форматирование литералов для simpleeval (_quote_if_string).
- Двухпроходная подстановка: переменные → iif.
- Цветовые фильтры (|color) и цветовые функции внутри iif.
- Debug-фильтр (|debug).
- Маскирование @sensitive-свойств.
- Строгая обработка ошибок: LogTemplateError для всех невалидных случаев.

═══════════════════════════════════════════════════════════════════════════════
ОРГАНИЗАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- TestValidatePathSegments — статический метод _validate_path_segments.
- TestUnderscoreSecurityAllPaths — векторы атак через '_'-сегменты.
- TestNamespaceResolution — разрешение из var, state, scope, context, params.
- TestNestedNavigation — навигация через DotPathNavigator для разных типов.
- TestQuoteIfString — форматирование литералов для simpleeval.
- TestResolveColorName — три формата имени цвета и ошибки.
- TestColorFilters — постобработка цветовых маркеров → ANSI.
- TestDebugFilter — фильтр |debug вне и рядом с iif.
- TestSensitiveMasking — маскирование @sensitive-свойств.
- TestIifSubstitution — переменные внутри и вне {iif(...)}.
- TestSubstitutePublicAPI — полный цикл через substitute().
- TestErrorHandling — все сценарии LogTemplateError.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor
from action_machine.testing.stubs import ContextStub
from tests.domain_model import SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные модели для тестов
# ─────────────────────────────────────────────────────────────────────────────

class _SensitiveUser:
    """Объект с @sensitive-свойством для тестов маскирования."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        return self._token

    # Имитация @sensitive декоратора — вешаем _sensitive_config на getter
    token.fget._sensitive_config = {  # type: ignore[attr-defined]
        "enabled": True,
        "max_chars": 3,
        "char": "*",
        "max_percent": 50,
    }


class _SensitiveDisabledUser:
    """Объект с @sensitive(enabled=False) для тестов отключённого маскирования."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        return self._token

    token.fget._sensitive_config = {  # type: ignore[attr-defined]
        "enabled": False,
        "max_chars": 3,
        "char": "*",
        "max_percent": 50,
    }


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
    return LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test_aspect", nest_level=0)


@pytest.fixture()
def ctx() -> Context:
    """Контекст с тестовым пользователем."""
    return ContextStub()


@pytest.fixture()
def state() -> BaseState:
    """Пустой BaseState."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Пустой BaseParams."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
# _validate_path_segments — проверка всех сегментов на '_'
# ═════════════════════════════════════════════════════════════════════════════

class TestValidatePathSegments:
    """Проверка _validate_path_segments для всех позиций сегментов."""

    def test_normal_path_passes(self) -> None:
        """Обычный путь без подчёркиваний — проверка проходит."""
        # Act / Assert — не должно бросить исключение
        VariableSubstitutor._validate_path_segments("context", "user.user_id")

    def test_single_segment_passes(self) -> None:
        """Одиночный сегмент без подчёркивания — проверка проходит."""
        VariableSubstitutor._validate_path_segments("var", "amount")

    def test_underscore_first_segment_blocked(self) -> None:
        """Подчёркивание в первом сегменте → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_internal"):
            VariableSubstitutor._validate_path_segments("context", "_internal.public_key")

    def test_underscore_middle_segment_blocked(self) -> None:
        """Подчёркивание в промежуточном сегменте → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_private"):
            VariableSubstitutor._validate_path_segments("context", "user._private.name")

    def test_underscore_last_segment_blocked(self) -> None:
        """Подчёркивание в последнем сегменте → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_secret"):
            VariableSubstitutor._validate_path_segments("context", "user._secret")

    def test_dunder_segment_blocked(self) -> None:
        """Dunder-атрибут (__dict__) → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="__dict__"):
            VariableSubstitutor._validate_path_segments("context", "__dict__.keys")

    def test_dunder_chain_blocked(self) -> None:
        """Цепочка dunder-атрибутов → блокируется на первом."""
        with pytest.raises(LogTemplateError, match="__class__"):
            VariableSubstitutor._validate_path_segments("context", "__class__.__name__")


# ═════════════════════════════════════════════════════════════════════════════
# Безопасность — атаки через промежуточные '_'-сегменты
# ═════════════════════════════════════════════════════════════════════════════

class TestUnderscoreSecurityAllPaths:
    """Проверка блокировки подчёркиваний через полный цикл substitute()."""

    def test_underscore_in_first_segment_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """Шаблон {%context._internal.public} блокируется."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context._internal.public}", {}, scope, ctx, state, params)

    def test_underscore_in_middle_segment_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """Шаблон {%var.obj._hidden.value} блокируется."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%var.obj._hidden.value}", {"obj": {"_hidden": {"value": 1}}}, scope, ctx, state, params)

    def test_dunder_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """Шаблон {%context.__dict__.keys} блокируется."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context.__dict__.keys}", {}, scope, ctx, state, params)

    def test_last_segment_underscore_still_blocked(self, sub, scope, ctx, state, params) -> None:
        """Шаблон {%var._secret} блокируется (последний сегмент)."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%var._secret}", {"_secret": "hidden"}, scope, ctx, state, params)

    def test_underscore_in_iif_blocked(self, sub, scope, ctx, state, params) -> None:
        """Подчёркивание внутри iif тоже блокируется."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute(
                "{iif({%var._flag}; 'yes'; 'no')}",
                {"_flag": True},
                scope, ctx, state, params,
            )


# ═════════════════════════════════════════════════════════════════════════════
# Разрешение namespace: var, state, scope, context, params
# ═════════════════════════════════════════════════════════════════════════════

class TestNamespaceResolution:
    """Разрешение переменных из всех пяти namespace."""

    def test_var_simple(self, sub, scope, ctx, state, params) -> None:
        """Namespace var — простая переменная из словаря."""
        result = sub.substitute("{%var.amount}", {"amount": 100}, scope, ctx, state, params)
        assert "100" in result

    def test_var_nested_dict(self, sub, scope, ctx, state, params) -> None:
        """Namespace var — вложенный dict через dot-path."""
        result = sub.substitute("{%var.a.b.c}", {"a": {"b": {"c": "deep"}}}, scope, ctx, state, params)
        assert "deep" in result

    def test_state_variable(self, sub, scope, ctx, params) -> None:
        """Namespace state — значение из BaseState [2]."""
        st = BaseState(txn_id="TXN-001")
        result = sub.substitute("{%state.txn_id}", {}, scope, ctx, st, params)
        assert "TXN-001" in result

    def test_scope_variable(self, sub, ctx, state, params) -> None:
        """Namespace scope — поле из LogScope [3]."""
        sc = LogScope(machine="M", mode="test", action="MyAction", aspect="a", nest_level=0)
        result = sub.substitute("{%scope.action}", {}, sc, ctx, state, params)
        assert "MyAction" in result

    def test_context_nested_variable(self, sub, scope, state, params) -> None:
        """Namespace context — вложенные поля через dot-path [2]."""
        c = ContextStub()
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)
        assert "test_user" in result

    def test_params_variable(self, sub, scope, ctx, state) -> None:
        """Namespace params — поле из BaseParams [9]."""
        p = SimpleAction.Params(name="Alice")
        result = sub.substitute("{%params.name}", {}, scope, ctx, state, p)
        assert "Alice" in result

    def test_unknown_namespace_raises(self, sub, scope, ctx, state, params) -> None:
        """Неизвестный namespace → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            sub.substitute("{%unknown.field}", {}, scope, ctx, state, params)


# ═════════════════════════════════════════════════════════════════════════════
# Навигация по вложенным объектам
# ═════════════════════════════════════════════════════════════════════════════

class TestNestedNavigation:
    """Навигация через DotPathNavigator для разных типов объектов."""

    def test_dict_three_levels(self, sub, scope, ctx, state, params) -> None:
        """Трёхуровневый вложенный dict."""
        var = {"a": {"b": {"c": 42}}}
        result = sub.substitute("{%var.a.b.c}", var, scope, ctx, state, params)
        assert "42" in result

    def test_schema_nested(self, sub, scope, state, params) -> None:
        """Навигация по вложенным BaseSchema-объектам [2]."""
        c = ContextStub()
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)
        assert "test_user" in result

    def test_state_with_nested_dict(self, sub, scope, ctx, params) -> None:
        """BaseState с вложенным dict."""
        st = BaseState(nested={"key": "value"})
        result = sub.substitute("{%state.nested.key}", {}, scope, ctx, st, params)
        assert "value" in result

    def test_missing_variable_raises(self, sub, scope, ctx, state, params) -> None:
        """Несуществующая переменная → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.missing}", {}, scope, ctx, state, params)

    def test_missing_intermediate_key_raises(self, sub, scope, ctx, state, params) -> None:
        """Отсутствующий промежуточный ключ → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.a.missing.deep}", {"a": {"other": 1}}, scope, ctx, state, params)


# ═════════════════════════════════════════════════════════════════════════════
# _quote_if_string — форматирование литералов для simpleeval
# ═════════════════════════════════════════════════════════════════════════════

class TestQuoteIfString:
    """Форматирование значений для подстановки внутри iif [11]."""

    def test_boolean_true(self) -> None:
        """True → 'True' без кавычек."""
        assert VariableSubstitutor._quote_if_string(True) == "True"

    def test_boolean_false(self) -> None:
        """False → 'False' без кавычек."""
        assert VariableSubstitutor._quote_if_string(False) == "False"

    def test_integer(self) -> None:
        """Целое число → строка без кавычек."""
        assert VariableSubstitutor._quote_if_string(42) == "42"

    def test_float(self) -> None:
        """Дробное число → строка без кавычек."""
        assert VariableSubstitutor._quote_if_string(3.14) == "3.14"

    def test_plain_string(self) -> None:
        """Обычная строка → в одинарных кавычках."""
        assert VariableSubstitutor._quote_if_string("hello") == "'hello'"

    def test_string_with_single_quote(self) -> None:
        """Строка с кавычкой → экранируется."""
        result = VariableSubstitutor._quote_if_string("it's")
        assert "\\'" in result

    def test_color_marker_not_quoted(self) -> None:
        """Цветовой маркер → без кавычек."""
        marker = "__COLOR(red)error__COLOR_END__"
        assert VariableSubstitutor._quote_if_string(marker) == marker


# ═════════════════════════════════════════════════════════════════════════════
# _resolve_color_name — три формата цвета
# ═════════════════════════════════════════════════════════════════════════════

class TestResolveColorName:
    """Преобразование имени цвета в ANSI-код."""

    def test_simple_foreground(self, sub) -> None:
        """Простой foreground: green → ANSI 32."""
        assert sub._resolve_color_name("green") == "\033[32m"

    def test_background(self, sub) -> None:
        """Background с префиксом bg_: bg_red → ANSI 41."""
        assert sub._resolve_color_name("bg_red") == "\033[41m"

    def test_fg_on_bg(self, sub) -> None:
        """Комбинация fg_on_bg: red_on_blue → ANSI 31;44."""
        assert sub._resolve_color_name("red_on_blue") == "\033[31;44m"

    def test_unknown_foreground_raises(self, sub) -> None:
        """Неизвестный foreground → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="color"):
            sub._resolve_color_name("rainbow")

    def test_unknown_background_raises(self, sub) -> None:
        """Неизвестный bg_ → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("bg_rainbow")

    def test_unknown_fg_in_combo_raises(self, sub) -> None:
        """Неизвестный fg в fg_on_bg → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="foreground"):
            sub._resolve_color_name("fakefg_on_blue")

    def test_unknown_bg_in_combo_raises(self, sub) -> None:
        """Неизвестный bg в fg_on_bg → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("red_on_fakebg")


# ═════════════════════════════════════════════════════════════════════════════
# Цветовые фильтры — |color и постобработка маркеров
# ═════════════════════════════════════════════════════════════════════════════

class TestColorFilters:
    """Цветовые фильтры через |color и замена маркеров на ANSI."""

    def test_color_filter_produces_ansi(self, sub, scope, ctx, state, params) -> None:
        """Фильтр |red оборачивает значение в ANSI red."""
        result = sub.substitute("{%var.msg|red}", {"msg": "error"}, scope, ctx, state, params)
        assert "\033[31m" in result
        assert "error" in result
        assert "\033[0m" in result

    def test_color_filter_green(self, sub, scope, ctx, state, params) -> None:
        """Фильтр |green оборачивает значение в ANSI green."""
        result = sub.substitute("{%var.msg|green}", {"msg": "ok"}, scope, ctx, state, params)
        assert "\033[32m" in result

    def test_nested_color_markers(self, sub) -> None:
        """Вложенные цветовые маркеры обрабатываются изнутри наружу."""
        text = "__COLOR(red)outer __COLOR(green)inner__COLOR_END__ end__COLOR_END__"
        result = sub._apply_color_filters(text)
        assert "\033[31m" in result
        assert "\033[32m" in result
        assert "__COLOR" not in result

    def test_no_markers_unchanged(self, sub) -> None:
        """Строка без маркеров возвращается без изменений."""
        text = "plain text without colors"
        assert sub._apply_color_filters(text) == text


# ═════════════════════════════════════════════════════════════════════════════
# Debug-фильтр — |debug
# ═════════════════════════════════════════════════════════════════════════════

class TestDebugFilter:
    """Фильтр |debug выводит интроспекцию объекта [11]."""

    def test_debug_dict(self, sub, scope, ctx, state, params) -> None:
        """Debug для dict выводит ключи и значения."""
        result = sub.substitute("{%var.obj|debug}", {"obj": {"key": "val"}}, scope, ctx, state, params)
        assert "key" in result

    def test_debug_with_iif(self, sub, scope, ctx, state, params) -> None:
        """Debug и iif в одном шаблоне оба работают."""
        template = "{%var.obj|debug} - {iif({%var.x} > 0; 'ok'; 'fail')}"
        result = sub.substitute(template, {"obj": {"k": "v"}, "x": 1}, scope, ctx, state, params)
        assert "k" in result
        assert "ok" in result

    def test_debug_simple_value(self, sub, scope, ctx, state, params) -> None:
        """Debug для простого значения (строка)."""
        result = sub.substitute("{%var.name|debug}", {"name": "Alice"}, scope, ctx, state, params)
        assert "Alice" in result


# ═════════════════════════════════════════════════════════════════════════════
# Маскирование @sensitive-свойств
# ═════════════════════════════════════════════════════════════════════════════

class TestSensitiveMasking:
    """Маскирование значений свойств с @sensitive [12]."""

    def test_sensitive_property_masked(self, sub, scope, ctx, state, params) -> None:
        """Свойство с @sensitive маскируется в выводе."""
        user = _SensitiveUser(token="super_secret_token_123")
        result = sub.substitute("{%var.user.token}", {"user": user}, scope, ctx, state, params)
        # Значение замаскировано — полный токен не виден
        assert "super_secret_token_123" not in result
        assert "*" in result

    def test_sensitive_disabled_not_masked(self, sub, scope, ctx, state, params) -> None:
        """Свойство с @sensitive(enabled=False) не маскируется."""
        user = _SensitiveDisabledUser(token="visible_token")
        result = sub.substitute("{%var.user.token}", {"user": user}, scope, ctx, state, params)
        assert "visible_token" in result

    def test_regular_attribute_not_masked(self, sub, scope, ctx, state, params) -> None:
        """Обычный атрибут (без @sensitive) не маскируется."""
        result = sub.substitute("{%var.name}", {"name": "Alice"}, scope, ctx, state, params)
        assert result == "Alice"


# ═════════════════════════════════════════════════════════════════════════════
# iif — переменные внутри и вне {iif(...)}
# ═════════════════════════════════════════════════════════════════════════════

class TestIifSubstitution:
    """Двухпроходная подстановка: переменные → iif [11]."""

    def test_var_outside_and_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Переменная вне iif — plain, внутри iif — литерал."""
        template = "Label: {%var.label} Result: {iif({%var.x} > 0; 'pos'; 'neg')}"
        result = sub.substitute(template, {"label": "test", "x": 5}, scope, ctx, state, params)
        assert "Label: test" in result
        assert "pos" in result

    def test_boolean_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Булева переменная внутри iif — без кавычек."""
        result = sub.substitute("{iif({%var.flag}; 'yes'; 'no')}", {"flag": True}, scope, ctx, state, params)
        assert "yes" in result

    def test_integer_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Целое число внутри iif — без кавычек."""
        result = sub.substitute("{iif({%var.count} > 0; 'some'; 'none')}", {"count": 3}, scope, ctx, state, params)
        assert "some" in result

    def test_string_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Строка внутри iif — в кавычках."""
        result = sub.substitute("{iif({%var.status} == 'ok'; 'good'; 'bad')}", {"status": "ok"}, scope, ctx, state, params)
        assert "good" in result

    def test_multiple_vars_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Несколько переменных внутри одного iif."""
        result = sub.substitute("{iif({%var.x} + {%var.y} > 10; 'big'; 'small')}", {"x": 7, "y": 5}, scope, ctx, state, params)
        assert "big" in result

    def test_iif_false_branch(self, sub, scope, ctx, state, params) -> None:
        """iif возвращает false-ветку при невыполненном условии."""
        result = sub.substitute("{iif({%var.x} > 100; 'big'; 'small')}", {"x": 5}, scope, ctx, state, params)
        assert "small" in result


# ═════════════════════════════════════════════════════════════════════════════
# substitute() — полный цикл публичного API
# ═════════════════════════════════════════════════════════════════════════════

class TestSubstitutePublicAPI:
    """Полный цикл через единственный публичный метод substitute()."""

    def test_plain_text_no_variables(self, sub, scope, ctx, state, params) -> None:
        """Текст без переменных возвращается как есть."""
        result = sub.substitute("Hello, world!", {}, scope, ctx, state, params)
        assert result == "Hello, world!"

    def test_single_variable(self, sub, scope, ctx, state, params) -> None:
        """Одна переменная подставляется."""
        result = sub.substitute("Amount: {%var.amount}", {"amount": 99.9}, scope, ctx, state, params)
        assert "99.9" in result

    def test_multiple_variables(self, sub, scope, ctx, state, params) -> None:
        """Несколько переменных из разных namespace."""
        st = BaseState(txn="TXN-1")
        sc = LogScope(machine="M", mode="test", action="Act", aspect="a", nest_level=0)
        result = sub.substitute(
            "var={%var.x} state={%state.txn} scope={%scope.action}",
            {"x": 42}, sc, ctx, st, params,
        )
        assert "42" in result
        assert "TXN-1" in result
        assert "Act" in result

    def test_variable_with_color_and_iif(self, sub, scope, ctx, state, params) -> None:
        """Цвет + iif + обычная переменная в одном шаблоне."""
        template = "{%var.label|green} {iif({%var.x} > 0; 'pos'; 'neg')}"
        result = sub.substitute(template, {"label": "Status", "x": 1}, scope, ctx, state, params)
        assert "\033[32m" in result
        assert "Status" in result
        assert "pos" in result

    def test_empty_template(self, sub, scope, ctx, state, params) -> None:
        """Пустой шаблон → пустая строка."""
        result = sub.substitute("", {}, scope, ctx, state, params)
        assert result == ""


# ═════════════════════════════════════════════════════════════════════════════
# Обработка ошибок — LogTemplateError
# ═════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Все сценарии, ведущие к LogTemplateError."""

    def test_missing_variable_raises(self, sub, scope, ctx, state, params) -> None:
        """Несуществующая переменная → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.missing}", {}, scope, ctx, state, params)

    def test_unknown_namespace_raises(self, sub, scope, ctx, state, params) -> None:
        """Неизвестный namespace → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            sub.substitute("{%unknown.field}", {}, scope, ctx, state, params)

    def test_underscore_in_path_raises(self, sub, scope, ctx, state, params) -> None:
        """Подчёркивание в любом сегменте → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context._internal.key}", {}, scope, ctx, state, params)

    def test_unknown_color_raises(self, sub, scope, ctx, state, params) -> None:
        """Неизвестный цвет в фильтре → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="color"):
            sub.substitute("{%var.x|rainbow}", {"x": "test"}, scope, ctx, state, params)

    def test_missing_variable_in_iif_raises(self, sub, scope, ctx, state, params) -> None:
        """Несуществующая переменная внутри iif → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{iif({%var.missing} > 0; 'a'; 'b')}", {}, scope, ctx, state, params)

    def test_underscore_in_iif_raises(self, sub, scope, ctx, state, params) -> None:
        """Подчёркивание внутри iif → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{iif({%var._hidden}; 'a'; 'b')}", {"_hidden": True}, scope, ctx, state, params)
