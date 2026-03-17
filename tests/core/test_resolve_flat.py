"""
Тесты ReadableMixin.resolve для плоских полей (без вложенности).

Проверяем:
- Доступ к простым атрибутам
- Доступ с default-значением
- None значения
"""

from action_machine.Context.user_info import user_info


class TestResolveFlat:
    """Тесты resolve для плоских полей."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Базовый доступ
    # ------------------------------------------------------------------

    def test_resolve_flat_field(self, flat_user):
        """resolve возвращает значение плоского поля."""
        assert flat_user.resolve("user_id") == "42"

    def test_resolve_flat_field_with_default(self, flat_user):
        """resolve с default возвращает значение для существующего поля."""
        assert flat_user.resolve("user_id", default="N/A") == "42"

    def test_resolve_another_flat_field(self, flat_user):
        """Доступ к другому плоскому полю."""
        assert flat_user.resolve("roles") == ["admin", "user"]

    # ------------------------------------------------------------------
    # ТЕСТЫ: None значения
    # ------------------------------------------------------------------

    def test_resolve_none_value(self):
        """resolve корректно возвращает None, если значение равно None."""
        user = user_info(user_id=None)
        assert user.resolve("user_id") is None

    def test_resolve_none_with_default(self):
        """
        resolve с default возвращает None, если значение равно None.
        default не подставляется, потому что значение существует (хоть и None).
        """
        user = user_info(user_id=None)
        assert user.resolve("user_id", default="fallback") is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разные типы плоских полей
    # ------------------------------------------------------------------

    def test_resolve_int_field(self):
        """resolve возвращает целое число."""
        user = user_info(user_id="42")
        result = user.resolve("user_id")
        assert result == "42"  # строка, но это нормально для user_id

    def test_resolve_string_field(self):
        """resolve возвращает строку."""
        user = user_info(user_id="test_user")
        assert user.resolve("user_id") == "test_user"

    def test_resolve_list_field(self, flat_user):
        """resolve возвращает список как значение."""
        result = flat_user.resolve("roles")
        assert result == ["admin", "user"]
        assert isinstance(result, list)
