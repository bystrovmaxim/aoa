# tests2/logging/test_expression_evaluator.py
"""
Тесты ExpressionEvaluator — безопасного вычислителя выражений для шаблонов логирования.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ExpressionEvaluator использует библиотеку simpleeval для безопасного вычисления
выражений внутри конструкции {iif(condition; true_value; false_value)}.
Обеспечивает:

- Операторы сравнения, логические, арифметические.
- Встроенные функции: len, upper, lower, format_number, str, int, float, abs.
- Цветовые функции: red, green, blue и др. (оборачивают в маркеры).
- Функцию debug(obj) — интроспекция объектов.
- Функцию exists(name) — проверка существования переменной.

Все вычисления безопасны: simpleeval не даёт доступа к файловой системе,
сети и встроенным опасным функциям.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

evaluate() — простые выражения:
    - Числовые сравнения.
    - Арифметические операции.
    - Логические операторы (and, or, not).
    - Строковые сравнения.
    - Встроенные функции (len, upper, lower, format_number, str, int, float, abs).
    - Цветовые функции (обёртка в маркер __COLOR(...)__COLOR_END__).

evaluate_iif() — конструкция iif:
    - Базовый iif с литералами и переменными.
    - Вложенные iif.
    - Разбор аргументов с учётом вложенных скобок и строковых литералов.
    - Обработка строк с точкой с запятой внутри.

process_template() — замена всех {iif(...)} в строке:
    - Одиночный iif.
    - Несколько iif.
    - iif в начале/конце строки.

Ошибки:
    - Неверное количество аргументов iif → LogTemplateError.
    - Неопределённая переменная → LogTemplateError.
    - Синтаксическая ошибка в выражении → LogTemplateError.
    - Деление на ноль → LogTemplateError.
"""

import pytest

from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.expression_evaluator import ExpressionEvaluator, _IifArgSplitter


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    """Свежий ExpressionEvaluator для каждого теста."""
    return ExpressionEvaluator()


# ======================================================================
# ТЕСТЫ: evaluate() — простые выражения
# ======================================================================

class TestEvaluateSimple:
    """Базовые арифметические и логические выражения."""

    def test_numeric_comparison(self, evaluator: ExpressionEvaluator) -> None:
        """Сравнение чисел."""
        names = {"amount": 1500}
        assert evaluator.evaluate("amount > 1000", names) is True
        assert evaluator.evaluate("amount <= 1000", names) is False

    def test_arithmetic(self, evaluator: ExpressionEvaluator) -> None:
        """Арифметические операции."""
        names = {"x": 10, "y": 3}
        assert evaluator.evaluate("x + y", names) == 13
        assert evaluator.evaluate("x - y", names) == 7
        assert evaluator.evaluate("x * y", names) == 30
        assert evaluator.evaluate("x / y", names) == 10 / 3
        assert evaluator.evaluate("x % y", names) == 1

    def test_string_comparison(self, evaluator: ExpressionEvaluator) -> None:
        """Сравнение строк."""
        names = {"status": "active"}
        assert evaluator.evaluate("status == 'active'", names) is True
        assert evaluator.evaluate("status != 'active'", names) is False

    def test_logical_operators(self, evaluator: ExpressionEvaluator) -> None:
        """Логические операторы."""
        names = {"x": 5, "y": 10}
        assert evaluator.evaluate("x > 3 and y < 20", names) is True
        assert evaluator.evaluate("x > 10 or y < 5", names) is False
        assert evaluator.evaluate("not (x > 10)", names) is True

    def test_parentheses(self, evaluator: ExpressionEvaluator) -> None:
        """Приоритет операций со скобками."""
        names = {"x": 5, "y": 10, "z": 2}
        assert evaluator.evaluate("x + y * z", names) == 25
        assert evaluator.evaluate("(x + y) * z", names) == 30


class TestEvaluateBuiltins:
    """Встроенные функции."""

    def test_len_upper_lower(self, evaluator: ExpressionEvaluator) -> None:
        """len, upper, lower."""
        names = {"text": "Hello", "items": [1, 2, 3]}
        assert evaluator.evaluate("len(items)", names) == 3
        assert evaluator.evaluate("upper(text)", names) == "HELLO"
        assert evaluator.evaluate("lower(text)", names) == "hello"

    def test_str_int_float_abs(self, evaluator: ExpressionEvaluator) -> None:
        """str, int, float, abs."""
        names = {"s": "123", "f": 45.67, "x": -42}
        assert evaluator.evaluate("str(42)", names) == "42"
        assert evaluator.evaluate("int(s)", names) == 123
        assert evaluator.evaluate("int(f)", names) == 45
        assert evaluator.evaluate("float(s)", names) == 123.0
        assert evaluator.evaluate("abs(x)", names) == 42

    def test_format_number(self, evaluator: ExpressionEvaluator) -> None:
        """format_number(value, decimals)."""
        names = {"value": 1234567.89}
        assert evaluator.evaluate("format_number(value, 0)", names) == "1,234,568"
        assert evaluator.evaluate("format_number(value, 2)", names) == "1,234,567.89"

    def test_color_functions_return_markers(self, evaluator: ExpressionEvaluator) -> None:
        """Цветовые функции возвращают маркеры __COLOR(color)text__COLOR_END__."""
        names = {}
        assert evaluator.evaluate("red('alert')", names) == "__COLOR(red)alert__COLOR_END__"
        assert evaluator.evaluate("green('ok')", names) == "__COLOR(green)ok__COLOR_END__"


# ======================================================================
# ТЕСТЫ: evaluate_iif() — конструкция iif
# ======================================================================

class TestEvaluateIifBasic:
    """Базовые конструкции iif."""

    def test_iif_with_literals(self, evaluator: ExpressionEvaluator) -> None:
        """iif с литералами."""
        assert evaluator.evaluate_iif("1 > 0; 'yes'; 'no'", {}) == "yes"
        assert evaluator.evaluate_iif("1 < 0; 'yes'; 'no'", {}) == "no"

    def test_iif_with_variables(self, evaluator: ExpressionEvaluator) -> None:
        """iif с переменными."""
        names = {"amount": 1500}
        assert evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names) == "HIGH"

    def test_iif_without_quotes_in_branches(self, evaluator: ExpressionEvaluator) -> None:
        """Ветки могут быть без кавычек (числа, переменные)."""
        names = {"value": 10, "threshold": 5}
        assert evaluator.evaluate_iif("value > threshold; value * 2; value / 2", names) == "20"

    def test_iif_with_boolean_literals(self, evaluator: ExpressionEvaluator) -> None:
        """Булевы литералы."""
        names = {"success": True}
        assert evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names) == "OK"
        assert evaluator.evaluate_iif("success; 'OK'; 'FAIL'", names) == "OK"

    def test_iif_with_complex_condition(self, evaluator: ExpressionEvaluator) -> None:
        """Сложное условие с and/or."""
        names = {"age": 25, "has_license": True}
        assert evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names) == "CAN_DRIVE"


class TestEvaluateIifNested:
    """Вложенные iif."""

    def test_nested_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Один уровень вложенности."""
        names = {"amount": 1500000}
        expr = "amount > 1000000; 'CRITICAL'; iif(amount > 100000; 'HIGH'; 'NORMAL')"
        assert evaluator.evaluate_iif(expr, names) == "CRITICAL"

        names2 = {"amount": 500000}
        assert evaluator.evaluate_iif(expr, names2) == "HIGH"

        names3 = {"amount": 50000}
        assert evaluator.evaluate_iif(expr, names3) == "NORMAL"

    def test_deeply_nested_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Глубоко вложенные iif (три уровня)."""
        expr = "x > 100; 'A'; iif(x > 50; 'B'; iif(x > 10; 'C'; 'D'))"
        assert evaluator.evaluate_iif(expr, {"x": 150}) == "A"


class TestEvaluateIifStringHandling:
    """Обработка строк с кавычками и точками с запятой."""

    def test_string_with_semicolon(self, evaluator: ExpressionEvaluator) -> None:
        """Строковые литералы могут содержать точку с запятой."""
        names = {"lang": "ru"}
        expr = "lang == 'ru'; 'Привет; как дела?'; 'Hello; how are you?'"
        assert evaluator.evaluate_iif(expr, names) == "Привет; как дела?"

    def test_string_with_quotes(self, evaluator: ExpressionEvaluator) -> None:
        """Строки могут содержать кавычки (escaped)."""
        names = {"lang": "ru"}
        expr = "lang == 'ru'; 'Он сказал: \"Привет\"'; 'He said: \"Hello\"'"
        assert evaluator.evaluate_iif(expr, names) == 'Он сказал: "Привет"'


# ======================================================================
# ТЕСТЫ: process_template() — замена iif в строке
# ======================================================================

class TestProcessTemplate:
    """Замена всех {iif(...)} в строке."""

    def test_no_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Шаблон без iif возвращается без изменений."""
        template = "Simple message"
        assert evaluator.process_template(template, {}) == template

    def test_single_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Один iif в середине строки."""
        names = {"success": True}
        template = "Status: {iif(success == True; 'OK'; 'FAIL')}"
        assert evaluator.process_template(template, names) == "Status: OK"

    def test_multiple_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Несколько iif в одной строке."""
        names = {"x": 5, "y": 10}
        template = "{iif(x > 3; 'A'; 'B')} and {iif(y < 5; 'C'; 'D')}"
        assert evaluator.process_template(template, names) == "A and D"

    def test_iif_at_beginning(self, evaluator: ExpressionEvaluator) -> None:
        """iif в начале строки."""
        names = {"count": 150}
        template = "{iif(count > 100; 'Many'; 'Few')} items"
        assert evaluator.process_template(template, names) == "Many items"

    def test_iif_at_end(self, evaluator: ExpressionEvaluator) -> None:
        """iif в конце строки."""
        names = {"success": False}
        template = "Result: {iif(success; 'OK'; 'Error')}"
        assert evaluator.process_template(template, names) == "Result: Error"


# ======================================================================
# ТЕСТЫ: Разбор аргументов iif (_IifArgSplitter)
# ======================================================================

class TestIifArgSplitter:
    """Разбор строки аргументов iif с учётом вложенных скобок и кавычек."""

    def test_split_with_nested_parens(self) -> None:
        """Вложенные скобки в условии не мешают разделению."""
        raw = "a + (b * c) > 10; 'yes'; 'no'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "a + (b * c) > 10"
        assert parts[1].strip() == "'yes'"
        assert parts[2].strip() == "'no'"

    def test_split_with_string_containing_semicolon(self) -> None:
        """Строковые литералы с точкой с запятой не разбивают аргументы."""
        raw = "lang == 'ru'; 'Привет; как дела?'; 'Hello; how are you?'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "lang == 'ru'"
        assert parts[1] == " 'Привет; как дела?'"
        assert parts[2] == " 'Hello; how are you?'"

    def test_split_with_nested_iif(self) -> None:
        """Вложенный iif во второй ветке."""
        raw = "amount > 1000; 'HIGH'; iif(amount > 500; 'MEDIUM'; 'LOW')"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "amount > 1000"
        assert parts[1] == " 'HIGH'"
        assert parts[2] == " iif(amount > 500; 'MEDIUM'; 'LOW')"


# ======================================================================
# ТЕСТЫ: Обработка ошибок
# ======================================================================

class TestErrorHandling:
    """ExpressionEvaluator выбрасывает LogTemplateError при ошибках."""

    def test_iif_wrong_number_of_args(self, evaluator: ExpressionEvaluator) -> None:
        """iif с 2 аргументами вместо 3 → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            evaluator.evaluate_iif("amount > 1000; 'HIGH'", {})

    def test_iif_undefined_variable(self, evaluator: ExpressionEvaluator) -> None:
        """Переменная не определена → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Variable 'missing' not found"):
            evaluator.evaluate_iif("missing > 10; 'yes'; 'no'", {})

    def test_evaluate_invalid_expression(self, evaluator: ExpressionEvaluator) -> None:
        """Синтаксически неверное выражение → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            evaluator.evaluate(">>>invalid<<<", {})

    def test_iif_division_by_zero(self, evaluator: ExpressionEvaluator) -> None:
        """Деление на ноль → LogTemplateError."""
        names = {"x": 10, "y": 0}
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            evaluator.evaluate_iif("y == 0; x / y; x * 2", names)

    def test_process_template_invalid_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Невалидный iif внутри шаблона → LogTemplateError."""
        with pytest.raises(LogTemplateError):
            evaluator.process_template("Bad: {iif(x > 10; 'yes')}", {})

    def test_process_template_missing_variable(self, evaluator: ExpressionEvaluator) -> None:
        """Переменная не определена в iif → LogTemplateError."""
        with pytest.raises(LogTemplateError):
            evaluator.process_template("Result: {iif(missing > 10; 'yes'; 'no')}", {})
