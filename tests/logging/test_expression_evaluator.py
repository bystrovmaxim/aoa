"""
Тесты ExpressionEvaluator — безопасного вычислителя выражений для iif.

Проверяем:
- Базовые арифметические и логические операции
- Сравнение строк и чисел
- Встроенные функции (len, upper, lower, format_number)
- Конструкцию iif с разными условиями
- Вложенные iif
- Обработку ошибок (невалидные выражения, отсутствие переменных)
- Парсинг аргументов с кавычками и скобками
"""

import pytest

from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.ExpressionEvaluator import expression_evaluator


class TestExpressionEvaluator:
    """Тесты вычислителя выражений для iif."""

    # ------------------------------------------------------------------
    # НАСТРОЙКА
    # ------------------------------------------------------------------

    def setup_method(self) -> None:
        """Создаёт свежий экземпляр ExpressionEvaluator перед каждым тестом."""
        self.evaluator = expression_evaluator()

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate() — простые выражения
    # ------------------------------------------------------------------

    def test_evaluate_simple_condition(self) -> None:
        """Проверка простого условия с числами."""
        names: dict[str, object] = {"amount": 1500}
        result = self.evaluator.evaluate("amount > 1000", names)
        assert result is True

        result = self.evaluator.evaluate("amount <= 1000", names)
        assert result is False

    def test_evaluate_arithmetic(self) -> None:
        """Проверка арифметических операций."""
        names = {"x": 10, "y": 3}

        assert self.evaluator.evaluate("x + y", names) == 13
        assert self.evaluator.evaluate("x - y", names) == 7
        assert self.evaluator.evaluate("x * y", names) == 30
        assert self.evaluator.evaluate("x / y", names) == 10 / 3
        assert self.evaluator.evaluate("x % y", names) == 1

    def test_evaluate_string_comparison(self) -> None:
        """Проверка сравнения строк."""
        names: dict[str, object] = {"status": "active"}

        result = self.evaluator.evaluate("status == 'active'", names)
        assert result is True

        result = self.evaluator.evaluate("status != 'active'", names)
        assert result is False

    def test_evaluate_logical_operators(self) -> None:
        """Проверка логических операторов."""
        names = {"x": 5, "y": 10}

        result = self.evaluator.evaluate("x > 3 and y < 20", names)
        assert result is True

        result = self.evaluator.evaluate("x > 10 or y < 5", names)
        assert result is False

        result = self.evaluator.evaluate("not (x > 10)", names)
        assert result is True

    def test_evaluate_parentheses(self) -> None:
        """Проверка приоритета операций со скобками."""
        names = {"x": 5, "y": 10, "z": 2}

        assert self.evaluator.evaluate("x + y * z", names) == 25  # 5 + 20
        assert self.evaluator.evaluate("(x + y) * z", names) == 30  # 15 * 2

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate() — встроенные функции
    # ------------------------------------------------------------------

    def test_evaluate_builtin_functions(self) -> None:
        """Проверка встроенных функций len, upper, lower."""
        names = {"text": "Hello", "items": [1, 2, 3]}

        result = self.evaluator.evaluate("len(items)", names)
        assert result == 3

        result = self.evaluator.evaluate("upper(text)", names)
        assert result == "HELLO"

        result = self.evaluator.evaluate("lower(text)", names)
        assert result == "hello"

    def test_evaluate_str_function(self) -> None:
        """Проверка функции str для преобразования в строку."""
        names = {"num": 42, "flag": True}

        assert self.evaluator.evaluate("str(num)", names) == "42"
        assert self.evaluator.evaluate("str(flag)", names) == "True"
        assert self.evaluator.evaluate("str(None)", names) == "None"

    def test_evaluate_int_function(self) -> None:
        """Проверка функции int для преобразования в целое число."""
        names = {"s": "123", "f": 45.67}

        assert self.evaluator.evaluate("int(s)", names) == 123
        assert self.evaluator.evaluate("int(f)", names) == 45

    def test_evaluate_float_function(self) -> None:
        """Проверка функции float для преобразования в число с плавающей точкой."""
        names = {"s": "123.45", "i": 67}

        assert self.evaluator.evaluate("float(s)", names) == 123.45
        assert self.evaluator.evaluate("float(i)", names) == 67.0

    def test_evaluate_abs_function(self) -> None:
        """Проверка функции abs для модуля числа."""
        names = {"x": -42, "y": 3.14}

        assert self.evaluator.evaluate("abs(x)", names) == 42
        assert self.evaluator.evaluate("abs(y)", names) == 3.14

    def test_evaluate_format_number(self) -> None:
        """Проверка функции format_number."""
        names = {"value": 1234567.89}

        # Без десятичных знаков (округление)
        result = self.evaluator.evaluate("format_number(value, 0)", names)
        assert result == "1,234,568"  # округлилось

        # С двумя десятичными знаками
        result = self.evaluator.evaluate("format_number(value, 2)", names)
        assert result == "1,234,567.89"

        # Отрицательное число
        names2 = {"value": -9876.54}
        result = self.evaluator.evaluate("format_number(value, 1)", names2)
        assert result == "-9,876.5"

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate_iif() — базовая конструкция
    # ------------------------------------------------------------------

    def test_iif_basic(self) -> None:
        """Проверка базовой конструкции iif."""
        names = {"amount": 1500}
        result = self.evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names)
        assert result == "HIGH"

        names2 = {"amount": 500}
        result = self.evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names2)
        assert result == "LOW"

    def test_iif_without_quotes_in_branches(self) -> None:
        """Ветки iif могут быть без кавычек (числа, переменные)."""
        names = {"value": 10, "threshold": 5}

        result = self.evaluator.evaluate_iif("value > threshold; value * 2; value / 2", names)
        assert result == "20"

        names2 = {"value": 2}
        result = self.evaluator.evaluate_iif("value > 5; value * 2; value / 2", names2)
        assert result == "1.0"

    def test_iif_with_boolean_literals(self) -> None:
        """Проверка iif с булевыми литералами True/False."""
        names = {"success": True}
        result = self.evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names)
        assert result == "OK"

        names2 = {"success": False}
        result = self.evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names2)
        assert result == "FAIL"

    def test_iif_with_boolean_direct(self) -> None:
        """Условие может быть просто булевой переменной."""
        names = {"enabled": True}
        result = self.evaluator.evaluate_iif("enabled; 'ON'; 'OFF'", names)
        assert result == "ON"

        names2 = {"enabled": False}
        result = self.evaluator.evaluate_iif("enabled; 'ON'; 'OFF'", names2)
        assert result == "OFF"

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate_iif() — вложенные конструкции
    # ------------------------------------------------------------------

    def test_iif_nested(self) -> None:
        """Проверка вложенных iif."""
        names = {"amount": 1500000}
        expr = "amount > 1000000; 'CRITICAL'; iif(amount > 100000; 'HIGH'; 'NORMAL')"

        result = self.evaluator.evaluate_iif(expr, names)
        assert result == "CRITICAL"

        names2 = {"amount": 500000}
        result = self.evaluator.evaluate_iif(expr, names2)
        assert result == "HIGH"

        names3 = {"amount": 50000}
        result = self.evaluator.evaluate_iif(expr, names3)
        assert result == "NORMAL"

    def test_iif_deeply_nested(self) -> None:
        """Глубоко вложенные iif (три уровня)."""
        names = {"x": 150}
        expr = "x > 100; 'A'; iif(x > 50; 'B'; iif(x > 10; 'C'; 'D'))"

        assert self.evaluator.evaluate_iif(expr, names) == "A"

        names2 = {"x": 75}
        assert self.evaluator.evaluate_iif(expr, names2) == "B"

        names3 = {"x": 30}
        assert self.evaluator.evaluate_iif(expr, names3) == "C"

        names4 = {"x": 5}
        assert self.evaluator.evaluate_iif(expr, names4) == "D"

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate_iif() — сложные условия
    # ------------------------------------------------------------------

    def test_iif_with_complex_condition(self) -> None:
        """Условие iif может содержать логические операторы."""
        names = {"age": 25, "has_license": True}

        result = self.evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names)
        assert result == "CAN_DRIVE"

        names2 = {"age": 16, "has_license": True}
        result = self.evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names2)
        assert result == "CANNOT_DRIVE"

    def test_iif_with_arithmetic_in_condition(self) -> None:
        """В условии iif можно использовать арифметику."""
        names = {"a": 10, "b": 20, "c": 5}

        result = self.evaluator.evaluate_iif("a + b > c * 5; 'YES'; 'NO'", names)
        # 10 + 20 = 30, c * 5 = 25 → 30 > 25 → YES
        assert result == "YES"

    # ------------------------------------------------------------------
    # ТЕСТЫ: evaluate_iif() — работа со строками
    # ------------------------------------------------------------------

    def test_iif_with_strings_containing_semicolon(self) -> None:
        """Строки в ветках могут содержать точку с запятой."""
        names = {"lang": "ru"}

        result = self.evaluator.evaluate_iif("lang == 'ru'; 'Привет; как дела?'; 'Hello; how are you?'", names)
        assert result == "Привет; как дела?"

    def test_iif_with_strings_containing_quotes(self) -> None:
        """Строки в ветках могут содержать кавычки (экранированные)."""
        names = {"lang": "ru"}

        result = self.evaluator.evaluate_iif("lang == 'ru'; 'Он сказал: \"Привет\"'; 'He said: \"Hello\"'", names)
        assert result == 'Он сказал: "Привет"'

    # ------------------------------------------------------------------
    # ТЕСТЫ: process_template() — замена iif в тексте
    # ------------------------------------------------------------------

    def test_process_template_no_iif(self) -> None:
        """Шаблон без iif возвращается без изменений."""
        template = "Простое сообщение"
        result = self.evaluator.process_template(template, {})
        assert result == template

    def test_process_template_single_iif(self) -> None:
        """Шаблон с одним iif."""
        names = {"success": True}
        template = "Статус: {iif(success == True; 'OK'; 'FAIL')}"
        result = self.evaluator.process_template(template, names)
        assert result == "Статус: OK"

    def test_process_template_multiple_iif(self) -> None:
        """Шаблон с несколькими iif."""
        names = {"x": 5, "y": 10}
        template = "{iif(x > 3; 'A'; 'B')} и {iif(y < 5; 'C'; 'D')}"
        result = self.evaluator.process_template(template, names)
        assert result == "A и D"

    def test_process_template_iif_at_beginning(self) -> None:
        """iif в начале строки."""
        names = {"count": 150}
        template = "{iif(count > 100; 'Много'; 'Мало')} элементов"
        result = self.evaluator.process_template(template, names)
        assert result == "Много элементов"

    def test_process_template_iif_at_end(self) -> None:
        """iif в конце строки."""
        names = {"success": False}
        template = "Результат: {iif(success; 'OK'; 'Ошибка')}"
        result = self.evaluator.process_template(template, names)
        assert result == "Результат: Ошибка"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обработка ошибок
    # ------------------------------------------------------------------

    def test_iif_syntax_error_raises(self) -> None:
        """
        iif с неверным количеством аргументов выбрасывает LogTemplateError.
        """
        names: dict[str, object] = {}

        with pytest.raises(LogTemplateError, match="iif ожидает 3 аргумента"):
            self.evaluator.evaluate_iif("amount > 1000; 'HIGH'", names)

    def test_iif_undefined_variable_raises(self) -> None:
        """
        Обращение к неопределённой переменной в iif выбрасывает LogTemplateError.
        """
        names: dict[str, object] = {}

        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate_iif("missing > 10; 'yes'; 'no'", names)

    def test_evaluate_invalid_expression_raises(self) -> None:
        """
        Невалидное выражение в evaluate выбрасывает LogTemplateError.
        """
        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate(">>>invalid<<<", {})

    def test_iif_invalid_condition_raises(self) -> None:
        """
        Невалидное условие в iif выбрасывает LogTemplateError.
        """
        names = {"x": 10}

        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate_iif("x >>> 5; 'A'; 'B'", names)

    def test_iif_division_by_zero_raises(self) -> None:
        """
        Деление на ноль в iif выбрасывает LogTemplateError.
        """
        names = {"x": 10, "y": 0}

        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate_iif("y == 0; x / y; x * 2", names)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Литеральные значения (без names)
    # ------------------------------------------------------------------

    def test_iif_with_literal_values(self) -> None:
        """
        Проверка iif с уже подставленными литеральными значениями.
        simpleeval получает числа/строки как литералы, names={}.
        """
        # Числовое сравнение — значения уже подставлены как литералы
        result = self.evaluator.evaluate_iif("1500.0 > 1000; 'HIGH'; 'LOW'", {})
        assert result == "HIGH"

        result = self.evaluator.evaluate_iif("500.0 > 1000; 'HIGH'; 'LOW'", {})
        assert result == "LOW"

    def test_iif_with_literal_string_comparison(self) -> None:
        """
        Проверка iif со строковым сравнением через литералы.
        """
        result = self.evaluator.evaluate_iif("'admin' == 'admin'; 'ROOT'; 'USER'", {})
        assert result == "ROOT"

        result = self.evaluator.evaluate_iif("'agent_1' == 'admin'; 'ROOT'; 'USER'", {})
        assert result == "USER"

    def test_iif_with_literal_bool(self) -> None:
        """
        Проверка iif с булевыми литералами.
        """
        result = self.evaluator.evaluate_iif("True == True; 'OK'; 'FAIL'", {})
        assert result == "OK"

        result = self.evaluator.evaluate_iif("False == True; 'OK'; 'FAIL'", {})
        assert result == "FAIL"

    def test_iif_with_literal_arithmetic(self) -> None:
        """Проверка iif с арифметикой на литералах."""
        result = self.evaluator.evaluate_iif("10 + 20 > 25; 'YES'; 'NO'", {})
        assert result == "YES"

    # ------------------------------------------------------------------
    # ТЕСТЫ: process_template с ошибками
    # ------------------------------------------------------------------

    def test_process_template_invalid_iif_raises(self) -> None:
        """
        Невалидный iif внутри шаблона выбрасывает LogTemplateError.
        """
        with pytest.raises(LogTemplateError):
            self.evaluator.process_template("Result: {iif(missing > 10; 'yes'; 'no')}", {})

    def test_process_template_with_malformed_iif_raises(self) -> None:
        """
        iif с неправильным синтаксисом внутри шаблона выбрасывает ошибку.
        """
        with pytest.raises(LogTemplateError):
            self.evaluator.process_template("Bad: {iif(x > 10; 'yes')}", {})
