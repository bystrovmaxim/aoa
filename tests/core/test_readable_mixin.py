# tests/core/test_readable_mixin.py
"""
Тесты ReadableMixin — дополнительные проверки, не покрытые основными тестами resolve.

Проверяем:
- Метод _resolve_step_generic возвращает _SENTINEL для несуществующего атрибута
- Методы keys/values/items исключают приватные поля (начинающиеся с _)
"""

from action_machine.Core.ReadableMixin import ReadableMixin


class SampleReadable(ReadableMixin):
    """Тестовый класс с публичными и приватными полями."""
    def __init__(self):
        self.public = "value"
        self._private = 42
        self.__mangled = "mangled"


class TestReadableMixin:
    """Дополнительные тесты для ReadableMixin."""

    def test_resolve_step_generic_returns_sentinel_for_missing(self):
        """_resolve_step_generic возвращает _SENTINEL для несуществующего атрибута."""
        obj = SampleReadable()
        # Получаем доступ к _SENTINEL через результат вызова с заведомо отсутствующим ключом
        # Но _SENTINEL — внутренняя константа, не экспортируется.
        # Вместо этого проверим, что метод resolve с таким путём вернёт default.
        # Это косвенно тестирует возврат _SENTINEL.
        result = obj.resolve("nonexistent", default="fallback")
        assert result == "fallback"

    def test_keys_excludes_private_attributes(self):
        """keys() не включает атрибуты, начинающиеся с '_'."""
        obj = SampleReadable()
        keys = obj.keys()
        assert "public" in keys
        assert "_private" not in keys
        assert "__mangled" not in keys
        assert len(keys) == 1

    def test_values_returns_public_values_only(self):
        """values() возвращает значения только публичных полей."""
        obj = SampleReadable()
        values = obj.values()
        assert values == ["value"]

    def test_items_returns_public_pairs_only(self):
        """items() возвращает пары (ключ, значение) только для публичных полей."""
        obj = SampleReadable()
        items = obj.items()
        assert items == [("public", "value")]