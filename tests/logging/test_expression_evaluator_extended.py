# tests/logging/test_expression_evaluator_extended.py
"""
Дополнительные тесты ExpressionEvaluator, specifically для _IifArgSplitter.
Проверяем:
- Разбиение аргументов iif с вложенными скобками
- Разбиение аргументов iif со строкой, содержащей точку с запятой
"""
from action_machine.logging.expression_evaluator import _IifArgSplitter


class TestIifArgSplitter:
    """Тесты внутреннего парсера аргументов iif."""

    def test_split_with_nested_parens(self):
        """Корректно разделяет аргументы при наличии вложенных скобок."""
        raw = "a + (b * c) > 10; 'yes'; 'no'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "a + (b * c) > 10"
        assert parts[1].strip() == "'yes'"
        assert parts[2].strip() == "'no'"

    def test_split_with_string_containing_semicolon(self):
        """Корректно обрабатывает строковые литералы с точкой с запятой."""
        raw = "lang == 'ru'; 'Привет; как дела?'; 'Hello; how are you?'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "lang == 'ru'"
        assert parts[1] == " 'Привет; как дела?'"
        assert parts[2] == " 'Hello; how are you?'"

    def test_split_with_nested_iif(self):
        """Корректно разделяет аргументы, когда внутри есть вложенный iif."""
        raw = "amount > 1000; 'HIGH'; iif(amount > 500; 'MEDIUM'; 'LOW')"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "amount > 1000"
        assert parts[1] == " 'HIGH'"
        assert parts[2] == " iif(amount > 500; 'MEDIUM'; 'LOW')"
