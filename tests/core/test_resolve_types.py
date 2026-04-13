# tests/core/test_resolve_types.py
"""
Тесты BaseSchema.resolve() для разных типов данных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve() возвращает значения любых типов без преобразования. Тип значения
определяется тем, что хранится в поле объекта или ключе словаря.
resolve не выполняет приведение типов, сериализацию или десериализацию —
возвращает ровно то, что записано.

Важный нюанс: resolve различает "значение существует и равно falsy"
(None, 0, False, "", []) и "значение отсутствует". Все falsy-значения —
валидные результаты, не заменяемые на default.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Строки:
    - Обычная строка — возвращается как есть.
    - Пустая строка "" — валидное значение, не отсутствие.

Числа:
    - int — возвращается как int.
    - float — возвращается как float.
    - Ноль (0, 0.0) — валидное значение, не отсутствие.

Булевы:
    - True — возвращается как True.
    - False — валидное значение, не отсутствие.

None:
    - None как значение поля — валидный результат.

Коллекции:
    - list — возвращается целиком.
    - Пустой list [] — валидное значение.
    - dict — возвращается целиком.
    - Пустой dict {} — валидное значение.

Вложенные структуры со смешанными типами:
    - dict внутри наследника с разными типами значений.
    - Доступ к bool, int, list внутри вложенных словарей.

Pydantic-модели:
    - resolve на BaseParams с типизированными полями.
"""

from typing import Any

from pydantic import ConfigDict, Field

from action_machine.intents.context.context import Context
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.scenarios.domain_model.roles import AdminRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Наследник UserInfo для тестов вложенных структур
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """Наследник UserInfo с dict-полем для тестов вложенной навигации."""
    model_config = ConfigDict(frozen=True)
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная pydantic-модель с разными типами полей
# ═════════════════════════════════════════════════════════════════════════════


class TypedParams(BaseParams):
    """
    Параметры с полями разных типов для тестирования resolve.
    """
    int_val: int = Field(default=42, description="Целое число")
    float_val: float = Field(default=3.14, description="Число с плавающей точкой")
    str_val: str = Field(default="hello", description="Строка")
    bool_val: bool = Field(default=True, description="Булево значение")
    none_val: str | None = Field(default=None, description="Пустое значение")
    list_val: list = Field(default_factory=lambda: [1, 2, 3], description="Список")
    dict_val: dict = Field(default_factory=lambda: {"a": 1, "b": 2}, description="Словарь")


# ═════════════════════════════════════════════════════════════════════════════
# Строки
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveStrings:
    """resolve для строковых значений."""

    def test_regular_string(self) -> None:
        """Обычная строка — resolve возвращает её без изменений."""
        user = UserInfo(user_id="test_user")
        result = user.resolve("user_id")
        assert result == "test_user"
        assert isinstance(result, str)

    def test_empty_string_is_valid_value(self) -> None:
        """Пустая строка "" — валидное значение, не отсутствие поля."""
        user = UserInfo(user_id="")
        result = user.resolve("user_id")
        assert result == ""
        assert isinstance(result, str)


# ═════════════════════════════════════════════════════════════════════════════
# Числа
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNumbers:
    """resolve для числовых значений: int и float."""

    def test_int_value(self) -> None:
        """resolve возвращает int без приведения типа."""
        params = TypedParams()
        result = params.resolve("int_val")
        assert result == 42
        assert isinstance(result, int)

    def test_float_value(self) -> None:
        """resolve возвращает float без приведения типа."""
        params = TypedParams()
        result = params.resolve("float_val")
        assert result == 3.14
        assert isinstance(result, float)

    def test_zero_int_is_valid_value(self) -> None:
        """Числовой ноль 0 — валидное значение, не отсутствие."""
        state = BaseState(count=0)
        result = state.resolve("count")
        assert result == 0
        assert isinstance(result, int)

    def test_zero_float_is_valid_value(self) -> None:
        """Числовой ноль 0.0 (float) — валидное значение."""
        state = BaseState(total=0.0)
        result = state.resolve("total")
        assert result == 0.0
        assert isinstance(result, float)


# ═════════════════════════════════════════════════════════════════════════════
# Булевы значения
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveBooleans:
    """resolve для булевых значений: True и False."""

    def test_true_value(self) -> None:
        """resolve возвращает True без изменений."""
        params = TypedParams()
        result = params.resolve("bool_val")
        assert result is True

    def test_false_is_valid_value(self) -> None:
        """False — валидное значение, не отсутствие."""
        state = BaseState(active=False)
        result = state.resolve("active")
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNone:
    """resolve для None-значений — поле существует, значение None."""

    def test_none_field_value(self) -> None:
        """Поле со значением None — resolve возвращает None."""
        params = TypedParams()
        result = params.resolve("none_val")
        assert result is None

    def test_none_in_state(self) -> None:
        """None как значение в BaseState — resolve возвращает None."""
        state = BaseState(result=None)
        result = state.resolve("result")
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Коллекции: list и dict
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveCollections:
    """resolve для коллекций: list и dict."""

    def test_list_value(self) -> None:
        """resolve возвращает кортеж ролей целиком."""
        user = UserInfo(roles=(AdminRole, UserRole))
        result = user.resolve("roles")
        assert result == (AdminRole, UserRole)
        assert isinstance(result, tuple)

    def test_empty_list_is_valid_value(self) -> None:
        """Пустой кортеж ролей — валидное значение, не отсутствие."""
        user = UserInfo(roles=())
        result = user.resolve("roles")
        assert result == ()
        assert isinstance(result, tuple)

    def test_dict_value(self) -> None:
        """resolve возвращает словарь целиком."""
        params = TypedParams()
        result = params.resolve("dict_val")
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)

    def test_empty_dict_is_valid_value(self) -> None:
        """Пустой словарь {} — валидное значение, не отсутствие."""
        user = _ExtendedUserInfo(settings={})
        result = user.resolve("settings")
        assert result == {}
        assert isinstance(result, dict)

    def test_list_from_pydantic(self) -> None:
        """resolve на pydantic-модели возвращает list из Field(default_factory=...)."""
        params = TypedParams()
        result = params.resolve("list_val")
        assert result == [1, 2, 3]
        assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════════════
# Вложенные структуры со смешанными типами
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveMixedNested:
    """resolve через вложенные структуры с разными типами значений."""

    def test_nested_dict_with_various_types(self) -> None:
        """
        Словарь внутри наследника содержит значения разных типов.
        resolve корректно извлекает каждый тип из вложенной структуры.
        """
        # Arrange — наследник UserInfo с вложенным dict
        user = _ExtendedUserInfo(
            user_id="42",
            roles=(AdminRole,),
            settings={
                "notifications": {
                    "email": True,
                    "count": 5,
                    "channels": ["sms", "push"],
                },
            },
        )
        ctx = Context(user=user)

        # Act & Assert — булево из глубокой вложенности
        assert ctx.resolve("user.settings.notifications.email") is True

        # Act & Assert — числовое значение
        assert ctx.resolve("user.settings.notifications.count") == 5

        # Act & Assert — список
        channels = ctx.resolve("user.settings.notifications.channels")
        assert channels == ["sms", "push"]
        assert isinstance(channels, list)

    def test_dict_value_from_extended_field(self) -> None:
        """
        resolve до промежуточного уровня возвращает dict целиком.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"theme": "dark", "lang": "ru"})
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.settings")

        # Assert — весь вложенный словарь
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)
