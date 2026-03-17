"""
Тесты ReadableMixin.resolve для навигации по словарям внутри объектов.

Проверяем:
- Доступ к значениям в словарях
- Вложенные словари
- Отсутствие ключей в словарях
"""

from action_machine.Context.user_info import UserInfo


class TestResolveDict:
    """Тесты resolve для навигации по словарям."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Простые словари
    # ------------------------------------------------------------------

    def test_resolve_dict_inside_readable(self):
        """resolve проходит через dict внутри ReadableMixin."""
        user = UserInfo(extra={"nested": {"key": "value"}})
        assert user.resolve("extra.nested.key") == "value"

    def test_resolve_dict_inside_dict(self):
        """resolve проходит через вложенные словари."""
        user = UserInfo(extra={"level1": {"level2": {"value": 42}}})
        assert user.resolve("extra.level1.level2.value") == 42

    def test_resolve_dict_multiple_keys(self):
        """resolve получает несколько значений из словаря."""
        user = UserInfo(extra={"a": 1, "b": 2, "c": 3})
        assert user.resolve("extra.a") == 1
        assert user.resolve("extra.b") == 2
        assert user.resolve("extra.c") == 3

    # ------------------------------------------------------------------
    # ТЕСТЫ: Словари со сложными значениями
    # ------------------------------------------------------------------

    def test_resolve_dict_with_list(self):
        """resolve получает список из словаря."""
        user = UserInfo(extra={"items": [1, 2, 3, 4]})
        result = user.resolve("extra.items")
        assert result == [1, 2, 3, 4]
        assert isinstance(result, list)

    def test_resolve_dict_with_dict(self):
        """resolve получает вложенный словарь целиком."""
        user = UserInfo(extra={"config": {"theme": "dark", "lang": "ru"}})
        result = user.resolve("extra.config")
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отсутствующие ключи
    # ------------------------------------------------------------------

    def test_resolve_dict_with_missing_key(self):
        """resolve возвращает default при отсутствии ключа в словаре."""
        user = UserInfo(extra={"existing": "value"})
        assert user.resolve("extra.missing", default="not found") == "not found"

    def test_resolve_dict_with_missing_nested_key(self):
        """resolve возвращает default при отсутствии вложенного ключа."""
        user = UserInfo(extra={"level1": {"level2": {"value": 42}}})
        result = user.resolve("extra.level1.level2.missing", default="none")
        assert result == "none"

    def test_resolve_dict_with_missing_intermediate_key(self):
        """
        resolve возвращает default, если промежуточный ключ не найден.
        Например: extra.level1.missing.level3.value
        """
        user = UserInfo(extra={"level1": {"level2": {"value": 42}}})
        result = user.resolve("extra.level1.missing.level3.value", default="N/A")
        assert result == "N/A"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    def test_resolve_dict_empty(self):
        """resolve на пустом словаре возвращает default."""
        user = UserInfo(extra={})
        assert user.resolve("extra.key", default="empty") == "empty"

    def test_resolve_dict_with_none_value(self):
        """resolve возвращает None, если в словаре значение None."""
        user = UserInfo(extra={"key": None})
        assert user.resolve("extra.key") is None
        assert user.resolve("extra.key", default="fallback") is None  # default не срабатывает
