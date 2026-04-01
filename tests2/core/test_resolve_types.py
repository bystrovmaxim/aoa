# tests2/core/test_resolve_types.py
"""
Тесты ReadableMixin.resolve() для разных типов данных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve() возвращает значения любых типов без преобразования. Тип значения
определяется тем, что хранится в атрибуте объекта или ключе словаря.
resolve не выполняет приведение типов, сериализацию или десериализацию —
возвращает ровно то, что записано.

Важный нюанс: resolve различает "значение существует и равно falsy"
(None, 0, False, "", []) и "значение отсутствует" (_SENTINEL).
Все falsy-значения — валидные результаты, не заменяемые на default.

Этот файл проверяет корректность resolve для каждого типа данных,
который может встретиться в state, params, context и extra-словарях.

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
    - False — валидное значение, не отсутствие (не заменяется на default).

None:
    - None как значение поля — валидный результат.
    - Отличие от отсутствия поля покрыто в test_resolve_missing.py.

Коллекции:
    - list — возвращается целиком.
    - Пустой list [] — валидное значение.
    - dict — возвращается целиком.
    - Пустой dict {} — валидное значение.

Вложенные структуры со смешанными типами:
    - dict внутри dict с разными типами значений.
    - Доступ к bool, int, list внутри вложенных словарей.

Pydantic-модели:
    - resolve на BaseParams с типизированными полями.
"""

from pydantic import Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная pydantic-модель с разными типами полей
# ═════════════════════════════════════════════════════════════════════════════


class TypedParams(BaseParams):
    """
    Параметры с полями разных типов для тестирования resolve.

    Каждое поле имеет конкретный тип и description (обязательно
    для BaseParams через DescribedFieldsGateHost). Значения по умолчанию
    покрывают основные типы данных Python.
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
        """
        Обычная строка — resolve возвращает её без изменений.

        Строки — самый частый тип в state и params: user_id, txn_id,
        status, currency и т.д.
        """
        # Arrange — UserInfo со строковым user_id
        user = UserInfo(user_id="test_user")

        # Act — resolve извлекает строку из атрибута
        result = user.resolve("user_id")

        # Assert — строка возвращена как есть, тип сохранён
        assert result == "test_user"
        assert isinstance(result, str)

    def test_empty_string_is_valid_value(self) -> None:
        """
        Пустая строка "" — валидное значение, не отсутствие поля.

        resolve различает "" (атрибут существует, значение — пустая строка)
        и отсутствие атрибута (_SENTINEL). Пустая строка не заменяется
        на default, потому что _resolve_one_step вернул "" (не _SENTINEL).
        """
        # Arrange — user_id = пустая строка (не None, не отсутствие)
        user = UserInfo(user_id="")

        # Act — resolve находит атрибут, его значение — ""
        result = user.resolve("user_id")

        # Assert — пустая строка, тип str, не None
        assert result == ""
        assert isinstance(result, str)


# ═════════════════════════════════════════════════════════════════════════════
# Числа
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNumbers:
    """resolve для числовых значений: int и float."""

    def test_int_value(self) -> None:
        """
        resolve возвращает int без приведения типа.

        int — типичный тип для count, quantity, nest_level в state.
        """
        # Arrange — pydantic-модель с int-полем, default=42
        params = TypedParams()

        # Act — resolve извлекает значение из pydantic-атрибута
        result = params.resolve("int_val")

        # Assert — int, не float и не str
        assert result == 42
        assert isinstance(result, int)

    def test_float_value(self) -> None:
        """
        resolve возвращает float без приведения типа.

        float — типичный тип для amount, total, discount в state и params.
        """
        # Arrange — pydantic-модель с float-полем, default=3.14
        params = TypedParams()

        # Act — resolve извлекает float
        result = params.resolve("float_val")

        # Assert — float, не int
        assert result == 3.14
        assert isinstance(result, float)

    def test_zero_int_is_valid_value(self) -> None:
        """
        Числовой ноль 0 — валидное значение, не отсутствие.

        0 — falsy в Python, но resolve проверяет через _SENTINEL,
        а не через truthiness. Поэтому 0 не заменяется на default.
        """
        # Arrange — state с нулевым значением count
        state = BaseState({"count": 0})

        # Act — resolve находит атрибут со значением 0
        result = state.resolve("count")

        # Assert — числовой 0, тип int, не None
        assert result == 0
        assert isinstance(result, int)

    def test_zero_float_is_valid_value(self) -> None:
        """
        Числовой ноль 0.0 (float) — валидное значение.

        Аналогично int-нулю: 0.0 — falsy, но не _SENTINEL.
        """
        # Arrange — state с нулевой суммой
        state = BaseState({"total": 0.0})

        # Act — resolve находит атрибут со значением 0.0
        result = state.resolve("total")

        # Assert — float-ноль, не None
        assert result == 0.0
        assert isinstance(result, float)


# ═════════════════════════════════════════════════════════════════════════════
# Булевы значения
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveBooleans:
    """resolve для булевых значений: True и False."""

    def test_true_value(self) -> None:
        """
        resolve возвращает True без изменений.
        """
        # Arrange — pydantic-модель с bool-полем, default=True
        params = TypedParams()

        # Act — resolve извлекает булево значение
        result = params.resolve("bool_val")

        # Assert — True, тип bool (не int 1)
        assert result is True

    def test_false_is_valid_value(self) -> None:
        """
        False — валидное значение, не отсутствие.

        False — falsy в Python (как 0 и ""), но resolve различает
        "атрибут существует со значением False" и "атрибут не найден".
        """
        # Arrange — state с False-значением
        state = BaseState({"active": False})

        # Act — resolve находит атрибут со значением False
        result = state.resolve("active")

        # Assert — булев False, не None и не default
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveNone:
    """resolve для None-значений — поле существует, значение None."""

    def test_none_field_value(self) -> None:
        """
        Поле со значением None — resolve возвращает None.

        TypedParams.none_val имеет тип str | None и default=None.
        resolve находит атрибут, его значение — None. Это не _SENTINEL,
        поэтому default не применяется.
        """
        # Arrange — pydantic-модель с none_val=None (default)
        params = TypedParams()

        # Act — resolve извлекает None-значение
        result = params.resolve("none_val")

        # Assert — None из атрибута
        assert result is None

    def test_none_in_state(self) -> None:
        """
        None как значение в BaseState — resolve возвращает None.
        """
        # Arrange — state с явным None
        state = BaseState({"result": None})

        # Act — resolve находит атрибут, значение None
        result = state.resolve("result")

        # Assert — None, не default
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Коллекции: list и dict
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveCollections:
    """resolve для коллекций: list и dict."""

    def test_list_value(self) -> None:
        """
        resolve возвращает список целиком.

        resolve не поддерживает индексацию (list.0). Для доступа
        к элементу нужно получить список и обращаться к нему в коде.
        """
        # Arrange — UserInfo с полем roles (список)
        user = UserInfo(roles=["admin", "user"])

        # Act — resolve возвращает весь список
        result = user.resolve("roles")

        # Assert — список из двух элементов, тип list
        assert result == ["admin", "user"]
        assert isinstance(result, list)

    def test_empty_list_is_valid_value(self) -> None:
        """
        Пустой список [] — валидное значение, не отсутствие.

        [] — falsy, но не _SENTINEL. resolve возвращает [],
        а не default.
        """
        # Arrange — UserInfo с пустым списком ролей
        user = UserInfo(roles=[])

        # Act — resolve находит атрибут, значение — пустой список
        result = user.resolve("roles")

        # Assert — пустой список, тип list, не None
        assert result == []
        assert isinstance(result, list)

    def test_dict_value(self) -> None:
        """
        resolve возвращает словарь целиком если путь заканчивается
        на ключе со значением-dict.
        """
        # Arrange — pydantic-модель с dict-полем
        params = TypedParams()

        # Act — resolve возвращает весь словарь
        result = params.resolve("dict_val")

        # Assert — словарь с двумя ключами
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)

    def test_empty_dict_is_valid_value(self) -> None:
        """
        Пустой словарь {} — валидное значение, не отсутствие.
        """
        # Arrange — UserInfo с пустым extra
        user = UserInfo(extra={})

        # Act — resolve возвращает пустой dict
        result = user.resolve("extra")

        # Assert — пустой словарь, тип dict, не None
        assert result == {}
        assert isinstance(result, dict)

    def test_list_from_pydantic(self) -> None:
        """
        resolve на pydantic-модели возвращает list из Field(default_factory=...).
        """
        # Arrange — pydantic-модель с list-полем
        params = TypedParams()

        # Act — resolve извлекает список
        result = params.resolve("list_val")

        # Assert — список из default_factory
        assert result == [1, 2, 3]
        assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════════════
# Вложенные структуры со смешанными типами
# ═════════════════════════════════════════════════════════════════════════════


class TestResolveMixedNested:
    """resolve через вложенные структуры с разными типами значений."""

    def test_nested_dict_with_various_types(self) -> None:
        """
        Словарь внутри extra содержит значения разных типов.
        resolve корректно извлекает каждый тип из вложенной структуры.
        """
        # Arrange — UserInfo с extra, содержащим вложенный dict
        # с булевым, числовым и списковым значениями
        user = UserInfo(
            user_id="42",
            roles=["admin"],
            extra={
                "settings": {
                    "notifications": {
                        "email": True,
                        "count": 5,
                        "channels": ["sms", "push"],
                    },
                },
            },
        )
        ctx = Context(user=user)

        # Act & Assert — булево значение из глубокой вложенности
        # Context → UserInfo → extra (dict) → settings (dict) →
        # notifications (dict) → email (bool)
        assert ctx.resolve("user.extra.settings.notifications.email") is True

        # Act & Assert — числовое значение из того же уровня
        assert ctx.resolve("user.extra.settings.notifications.count") == 5

        # Act & Assert — список из глубокой вложенности
        channels = ctx.resolve("user.extra.settings.notifications.channels")
        assert channels == ["sms", "push"]
        assert isinstance(channels, list)

    def test_dict_value_from_extra(self) -> None:
        """
        resolve до промежуточного уровня возвращает dict целиком.

        Путь "user.extra.settings" заканчивается на ключе "settings",
        чьё значение — словарь. resolve возвращает весь словарь.
        """
        # Arrange — Context с вложенной структурой
        user = UserInfo(extra={"settings": {"theme": "dark", "lang": "ru"}})
        ctx = Context(user=user)

        # Act — resolve до промежуточного уровня
        result = ctx.resolve("user.extra.settings")

        # Assert — весь вложенный словарь
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)
