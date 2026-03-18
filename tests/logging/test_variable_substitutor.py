# tests/logging/test_variable_substitutor.py
"""
Дополнительные тесты для VariableSubstitutor.

Проверяем:
- _resolve_from_dict для вложенных путей
- _quote_if_string с апострофом внутри строки
"""


from action_machine.Logging.variable_substitutor import VariableSubstitutor


class TestVariableSubstitutorExtended:
    """Дополнительные тесты VariableSubstitutor."""

    def setup_method(self):
        self.substitutor = VariableSubstitutor()

    # ------------------------------------------------------------------
    # ТЕСТЫ: _resolve_from_dict
    # ------------------------------------------------------------------

    def test_resolve_from_dict_nested_path(self):
        """_resolve_from_dict находит значение по вложенному пути."""
        source = {"a": {"b": {"c": 42}}}
        result = self.substitutor._resolve_from_dict(source, "a.b.c")
        assert result == 42

    def test_resolve_from_dict_missing_key(self):
        """_resolve_from_dict возвращает None, если ключ отсутствует."""
        source = {"a": 1}
        result = self.substitutor._resolve_from_dict(source, "a.b")
        assert result is None

    def test_resolve_from_dict_missing_intermediate(self):
        """_resolve_from_dict возвращает None, если промежуточный ключ не словарь."""
        source = {"a": 1}
        result = self.substitutor._resolve_from_dict(source, "a.b.c")
        assert result is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: _quote_if_string
    # ------------------------------------------------------------------

    def test_quote_if_string_with_apostrophe(self):
        """_quote_if_string экранирует одинарные кавычки внутри строки."""
        result = self.substitutor._quote_if_string("it's ok")
        # Ожидаем: 'it\'s ok'
        assert result == "'it\\'s ok'"

    def test_quote_if_string_with_quotes(self):
        """_quote_if_string экранирует кавычки, но не добавляет лишних."""
        result = self.substitutor._quote_if_string('hello "world"')
        assert result == '\'hello "world"\''

    def test_quote_if_string_bool(self):
        """_quote_if_string для bool возвращает 'True'/'False' без кавычек."""
        assert self.substitutor._quote_if_string(True) == "True"
        assert self.substitutor._quote_if_string(False) == "False"

    def test_quote_if_string_number(self):
        """_quote_if_string для чисел возвращает строковое представление без кавычек."""
        assert self.substitutor._quote_if_string(42) == "42"
        assert self.substitutor._quote_if_string(3.14) == "3.14"