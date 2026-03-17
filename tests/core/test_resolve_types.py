"""
Тесты ReadableMixin.resolve для разных типов данных.

Проверяем:
- Списки
- Числа (int, float)
- Булевы значения
- Строки
- None
- Вложенные структуры
"""

from dataclasses import dataclass

from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.BaseParams import BaseParams


@dataclass
class ParamsWithTypes(BaseParams):
    """Параметры с разными типами данных для тестов."""

    int_val: int = 42
    float_val: float = 3.14
    str_val: str = "hello"
    bool_val: bool = True
    none_val: None = None
    list_val: list = None
    dict_val: dict = None

    def __post_init__(self):
        if self.list_val is None:
            self.list_val = [1, 2, 3]
        if self.dict_val is None:
            self.dict_val = {"a": 1, "b": 2}


class TestResolveTypes:
    """Тесты resolve для разных типов данных."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Списки
    # ------------------------------------------------------------------

    def test_resolve_list_field(self):
        """resolve возвращает список как значение."""
        user = UserInfo(roles=["admin", "user"])
        result = user.resolve("roles")
        assert result == ["admin", "user"]
        assert isinstance(result, list)

    def test_resolve_list_element(self):
        """
        resolve НЕ поддерживает индексацию списков.
        Нельзя получить доступ к элементу по индексу через dot-path.
        """
        user = UserInfo(roles=["admin", "user"])
        result = user.resolve("roles")  # получаем весь список
        assert isinstance(result, list)

        # А вот так нельзя (и не должно работать)
        # user.resolve("roles.0") — не поддерживается

    # ------------------------------------------------------------------
    # ТЕСТЫ: Числа
    # ------------------------------------------------------------------

    def test_resolve_int_field(self):
        """resolve возвращает целое число."""
        params = ParamsWithTypes()
        result = params.resolve("int_val")
        assert result == 42
        assert isinstance(result, int)

    def test_resolve_float_field(self):
        """resolve возвращает число с плавающей точкой."""
        params = ParamsWithTypes()
        result = params.resolve("float_val")
        assert result == 3.14
        assert isinstance(result, float)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Булевы значения
    # ------------------------------------------------------------------

    def test_resolve_boolean_true(self):
        """resolve возвращает True."""
        params = ParamsWithTypes()
        assert params.resolve("bool_val") is True

    def test_resolve_boolean_false(self):
        """resolve возвращает False."""

        @dataclass
        class TestParams(BaseParams):
            active: bool = False

        params = TestParams()
        assert params.resolve("active") is False

    # ------------------------------------------------------------------
    # ТЕСТЫ: Строки
    # ------------------------------------------------------------------

    def test_resolve_string_field(self):
        """resolve возвращает строку."""
        params = ParamsWithTypes()
        result = params.resolve("str_val")
        assert result == "hello"
        assert isinstance(result, str)

    # ------------------------------------------------------------------
    # ТЕСТЫ: None
    # ------------------------------------------------------------------

    def test_resolve_none_field(self):
        """resolve возвращает None."""
        params = ParamsWithTypes()
        assert params.resolve("none_val") is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Словари
    # ------------------------------------------------------------------

    def test_resolve_dict_field(self):
        """resolve возвращает словарь."""
        params = ParamsWithTypes()
        result = params.resolve("dict_val")
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)

    def test_resolve_dict_value(self):
        """resolve может получить значение из словаря по ключу."""
        user = UserInfo(extra={"config": {"theme": "dark"}})
        result = user.resolve("extra.config.theme")
        assert result == "dark"
        assert isinstance(result, str)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Вложенные структуры с разными типами
    # ------------------------------------------------------------------

    def test_resolve_nested_mixed_types(self):
        """resolve работает со смешанными типами в цепочке."""
        user = UserInfo(
            user_id="42",
            roles=["admin"],
            extra={"settings": {"notifications": {"email": True, "count": 5, "channels": ["sms", "push"]}}},
        )
        ctx = Context(user=user)

        # Булево значение
        assert ctx.resolve("user.extra.settings.notifications.email") is True

        # Число
        assert ctx.resolve("user.extra.settings.notifications.count") == 5

        # Список
        channels = ctx.resolve("user.extra.settings.notifications.channels")
        assert channels == ["sms", "push"]
        assert isinstance(channels, list)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    def test_resolve_empty_list(self):
        """resolve возвращает пустой список."""
        user = UserInfo(roles=[])
        result = user.resolve("roles")
        assert result == []
        assert isinstance(result, list)

    def test_resolve_empty_dict(self):
        """resolve возвращает пустой словарь."""
        user = UserInfo(extra={})
        result = user.resolve("extra")
        assert result == {}
        assert isinstance(result, dict)

    def test_resolve_empty_string(self):
        """resolve возвращает пустую строку."""
        user = UserInfo(user_id="")
        result = user.resolve("user_id")
        assert result == ""
        assert isinstance(result, str)
