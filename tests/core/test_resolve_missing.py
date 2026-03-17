"""
Тесты ReadableMixin.resolve для отсутствующих ключей.

Проверяем:
- Отсутствие плоского поля
- Отсутствие вложенного поля
- Отсутствие промежуточного ключа в цепочке
- Поведение default при отсутствии
"""

from action_machine.Context.UserInfo import user_info

from .conftest import make_context_with_user


class TestResolveMissing:
    """Тесты resolve для отсутствующих ключей."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отсутствие плоского поля
    # ------------------------------------------------------------------

    def test_resolve_missing_returns_default(self):
        """resolve возвращает default если путь не найден."""
        user = user_info(user_id="42")
        assert user.resolve("nonexistent", default="<none>") == "<none>"

    def test_resolve_none_default_is_none(self):
        """resolve по умолчанию возвращает None для несуществующего пути."""
        user = user_info(user_id="42")
        assert user.resolve("missing") is None

    def test_resolve_missing_key_does_not_raise(self):
        """resolve не выбрасывает исключение при отсутствии ключа."""
        user = user_info(user_id="42")

        # Не должно быть KeyError или AttributeError
        result = user.resolve("missing.key")
        assert result is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отсутствие вложенного поля
    # ------------------------------------------------------------------

    def test_resolve_missing_nested_returns_default(self):
        """resolve возвращает default если промежуточный ключ не найден."""
        ctx = make_context_with_user()
        assert ctx.resolve("user.nonexistent.deep", default="N/A") == "N/A"

    def test_resolve_missing_nested_with_default_none(self):
        """resolve с default=None возвращает None."""
        ctx = make_context_with_user()
        assert ctx.resolve("user.nonexistent.deep", default=None) is None

    def test_resolve_missing_nested_in_dict(self):
        """resolve возвращает default при отсутствии ключа в словаре."""
        user = user_info(extra={"existing": "value"})
        assert user.resolve("extra.missing.deep", default="not found") == "not found"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Отсутствие промежуточного ключа
    # ------------------------------------------------------------------

    def test_resolve_missing_intermediate_key(self):
        """
        Если промежуточный ключ не найден, возвращается default.
        Например: user.missing.key (где user есть, но missing нет)
        """
        ctx = make_context_with_user()
        result = ctx.resolve("user.missing.key.deep", default="fallback")
        assert result == "fallback"

    def test_resolve_missing_intermediate_in_dict(self):
        """
        Промежуточный ключ отсутствует в словаре.
        extra.existing.missing.deep
        """
        user = user_info(extra={"existing": {"key": "value"}})
        result = user.resolve("extra.existing.missing.deep", default="none")
        assert result == "none"

    def test_resolve_missing_first_segment(self):
        """Первый сегмент пути отсутствует."""
        user = user_info(user_id="42")
        result = user.resolve("missing.segment.deep", default="first missing")
        assert result == "first missing"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разные типы default
    # ------------------------------------------------------------------

    def test_resolve_default_string(self):
        """default может быть строкой."""
        user = user_info(user_id="42")
        assert user.resolve("missing", default="default string") == "default string"

    def test_resolve_default_int(self):
        """default может быть числом."""
        user = user_info(user_id="42")
        assert user.resolve("missing", default=42) == 42

    def test_resolve_default_list(self):
        """default может быть списком."""
        user = user_info(user_id="42")
        assert user.resolve("missing", default=[1, 2, 3]) == [1, 2, 3]

    def test_resolve_default_dict(self):
        """default может быть словарем."""
        user = user_info(user_id="42")
        assert user.resolve("missing", default={"key": "value"}) == {"key": "value"}

    def test_resolve_default_bool(self):
        """default может быть булевым значением.

        Кеш resolve привязан к dotpath, поэтому используем разные ключи
        (или разные экземпляры объекта) для True и False, чтобы
        первый вызов не закешировал результат для второго.
        """
        user1 = user_info(user_id="42")
        assert user1.resolve("missing_true", default=True) is True

        user2 = user_info(user_id="42")
        assert user2.resolve("missing_false", default=False) is False

    # ------------------------------------------------------------------
    # ТЕСТЫ: None как значение vs отсутствие
    # ------------------------------------------------------------------

    def test_resolve_none_value_vs_missing(self):
        """
        None как значение поля — это не то же самое, что отсутствие поля.
        Если поле есть и равно None, resolve возвращает None,
        даже если передан default.
        """
        user = user_info(user_id=None)
        assert user.resolve("user_id", default="fallback") is None

    def test_resolve_missing_vs_none_in_dict(self):
        """
        В словаре: ключ есть со значением None vs ключа нет.
        """
        user = user_info(extra={"key_with_none": None})

        # Ключ есть, значение None
        assert user.resolve("extra.key_with_none", default="fallback") is None

        # Ключа нет
        assert user.resolve("extra.missing_key", default="fallback") == "fallback"
