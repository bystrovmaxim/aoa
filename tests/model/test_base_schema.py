# tests/model/test_base_schema.py
"""
Тесты BaseSchema — базовая pydantic-схема с dict-подобным доступом к полям.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseSchema наследует pydantic.BaseModel и добавляет dict-подобный интерфейс
доступа к полям: __getitem__, __contains__, get, keys, values, items.

Все структуры данных фреймворка наследуют BaseSchema:
- BaseParams — входные параметры действия (frozen, forbid).
- BaseResult — результат действия (frozen, forbid).
- BaseState — состояние конвейера (frozen, allow).
- Context, UserInfo, RequestInfo, RuntimeInfo — контекст выполнения.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Плоский доступ:
    - keys() возвращает объявленные поля модели.
    - values() возвращает значения объявленных полей.
    - items() возвращает пары (ключ, значение).
    - __getitem__ возвращает значение, KeyError для отсутствующих.
    - __contains__ проверяет наличие поля.
    - get() возвращает значение или default.

Extra-поля (BaseState с extra="allow"):
    - keys/values/items включают динамические extra-поля.
    - __getitem__ работает для extra-полей.
    - __contains__ находит extra-поля.

Строгие модели (extra="forbid"):
    - Пустая модель возвращает пустые keys/values/items.
    - Модель с объявленными полями возвращает только их.

Pydantic-совместимость:
    - model_dump() сериализует все поля.
    - Frozen-модели запрещают запись.
"""

import pytest
from pydantic import ConfigDict, Field, ValidationError

from action_machine.model.base_result import BaseResult
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class SimpleSchema(BaseSchema):
    """
    Простая схема с несколькими полями для тестирования.
    Не frozen — разрешает запись для проверки базовых операций.
    """

    model_config = ConfigDict(frozen=False)

    name: str = ""
    value: int = 0
    active: bool = False


class FrozenSchema(BaseSchema):
    """Frozen-схема для проверки иммутабельности."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: float = 0.0


# ═════════════════════════════════════════════════════════════════════════════
# Плоский доступ: keys, values, items
# ═════════════════════════════════════════════════════════════════════════════


class TestKeysValuesItems:
    """Тесты keys(), values(), items() — итерация по полям схемы."""

    def test_keys_returns_declared_fields(self) -> None:
        """
        keys() возвращает список имён объявленных полей модели.

        Для pydantic-моделей BaseSchema использует model_fields.keys().
        Внутренние pydantic-атрибуты не попадают в результат.
        """
        # Arrange — схема с тремя полями
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        keys = obj.keys()

        # Assert — все три объявленных поля
        assert sorted(keys) == ["active", "name", "value"]

    def test_values_returns_field_values(self) -> None:
        """
        values() возвращает значения объявленных полей.
        Порядок соответствует порядку keys().
        """
        # Arrange
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        values = obj.values()

        # Assert — значения всех полей
        assert set(values) == {"test", 42, True}

    def test_items_returns_pairs(self) -> None:
        """
        items() возвращает пары (ключ, значение) для всех полей.
        """
        # Arrange
        obj = SimpleSchema(name="Alice", value=7, active=False)

        # Act
        items = dict(obj.items())

        # Assert — все пары
        assert items == {"name": "Alice", "value": 7, "active": False}

    def test_keys_for_empty_pydantic_model(self) -> None:
        """
        keys() для пустой pydantic-модели без полей возвращает пустой список.
        """
        # Arrange — BaseResult без объявленных полей
        result = BaseResult()

        # Act
        keys = result.keys()

        # Assert
        assert keys == []

    def test_keys_includes_extra_fields_for_state(self) -> None:
        """
        keys() для BaseState (extra="allow") включает динамические
        extra-поля, переданные при создании через kwargs.
        """
        # Arrange — BaseState с динамическими полями
        state = BaseState(total=1500, user="agent")

        # Act
        keys = state.keys()

        # Assert — extra-поля видны через keys()
        assert sorted(keys) == ["total", "user"]

    def test_values_includes_extra_for_state(self) -> None:
        """
        values() для BaseState включает значения extra-полей.
        """
        # Arrange
        state = BaseState(total=1500, user="agent")

        # Act
        values = state.values()

        # Assert
        assert set(values) == {1500, "agent"}

    def test_items_includes_extra_for_state(self) -> None:
        """
        items() для BaseState включает пары extra-полей.
        """
        # Arrange
        state = BaseState(count=42, flag=True)

        # Act
        items = dict(state.items())

        # Assert
        assert items == {"count": 42, "flag": True}


# ═════════════════════════════════════════════════════════════════════════════
# Плоский доступ: __getitem__, __contains__, get
# ═════════════════════════════════════════════════════════════════════════════


class TestDictAccess:
    """Тесты __getitem__, __contains__, get() — dict-подобный доступ."""

    def test_getitem_returns_value(self) -> None:
        """obj["key"] возвращает значение поля."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act
        result = obj["name"]

        # Assert
        assert result == "Alice"

    def test_getitem_missing_raises_key_error(self) -> None:
        """obj["missing"] бросает KeyError для несуществующего поля."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        with pytest.raises(KeyError):
            _ = obj["missing"]

    def test_getitem_on_state_extra_field(self) -> None:
        """__getitem__ работает для extra-полей BaseState."""
        # Arrange
        state = BaseState(txn_id="TXN-001")

        # Act
        result = state["txn_id"]

        # Assert
        assert result == "TXN-001"

    def test_contains_existing_key(self) -> None:
        """"key" in obj — True если поле существует."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        assert "name" in obj

    def test_contains_missing_key(self) -> None:
        """"missing" in obj — False если поле не существует."""
        # Arrange
        obj = SimpleSchema(name="Alice")

        # Act & Assert
        assert "missing" not in obj

    def test_contains_extra_field_in_state(self) -> None:
        """__contains__ находит extra-поля BaseState."""
        # Arrange
        state = BaseState(total=100)

        # Act & Assert
        assert "total" in state
        assert "missing" not in state

    def test_get_existing_key(self) -> None:
        """obj.get("key") возвращает значение существующего поля."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("value")

        # Assert
        assert result == 42

    def test_get_missing_key_returns_default(self) -> None:
        """obj.get("missing", default) возвращает default."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("missing", "fallback")

        # Assert
        assert result == "fallback"

    def test_get_missing_key_without_default_returns_none(self) -> None:
        """obj.get("missing") без default возвращает None."""
        # Arrange
        obj = SimpleSchema(value=42)

        # Act
        result = obj.get("missing")

        # Assert
        assert result is None

    def test_getitem_on_pydantic_result(self) -> None:
        """__getitem__ работает на pydantic BaseResult с объявленным полем."""

        # Arrange
        class _TestResult(BaseResult):
            metric: float = Field(description="Тестовая метрика")

        result = _TestResult(metric=99.5)

        # Act
        value = result["metric"]

        # Assert
        assert value == 99.5

        # Act & Assert — несуществующее поле
        with pytest.raises(KeyError):
            _ = result["nonexistent"]


# ═════════════════════════════════════════════════════════════════════════════
# Frozen-семантика
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozenSemantics:
    """Проверка иммутабельности frozen-схем."""

    def test_frozen_schema_rejects_write(self) -> None:
        """Frozen-схема запрещает запись атрибутов после создания."""
        # Arrange
        obj = FrozenSchema(metric=3.14)

        # Act & Assert — pydantic бросает ValidationError для frozen моделей
        with pytest.raises(ValidationError):
            obj.metric = 0.0

    def test_state_is_frozen(self) -> None:
        """BaseState (frozen=True) запрещает запись после создания."""
        # Arrange
        state = BaseState(total=100)

        # Act & Assert — pydantic бросает ValidationError для frozen моделей
        with pytest.raises(ValidationError):
            state.total = 200  # type: ignore[misc]

    def test_result_is_frozen(self) -> None:
        """BaseResult (frozen=True) запрещает запись после создания."""

        class _TestResult(BaseResult):
            status: str = Field(description="Статус")

        # Arrange
        result = _TestResult(status="ok")

        # Act & Assert — pydantic бросает ValidationError для frozen моделей
        with pytest.raises(ValidationError):
            result.status = "fail"  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Сериализация
# ═════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Проверка сериализации через model_dump()."""

    def test_model_dump_declared_fields(self) -> None:
        """model_dump() возвращает словарь объявленных полей."""
        # Arrange
        obj = SimpleSchema(name="test", value=42, active=True)

        # Act
        dumped = obj.model_dump()

        # Assert
        assert dumped == {"name": "test", "value": 42, "active": True}

    def test_model_dump_state_extra_fields(self) -> None:
        """model_dump() для BaseState включает extra-поля."""
        # Arrange
        state = BaseState(total=1500, user="agent")

        # Act
        dumped = state.model_dump()

        # Assert
        assert dumped == {"total": 1500, "user": "agent"}

    def test_state_to_dict(self) -> None:
        """BaseState.to_dict() эквивалентен model_dump()."""
        # Arrange
        state = BaseState(a=1, b="two")

        # Act
        result = state.to_dict()

        # Assert
        assert result == {"a": 1, "b": "two"}
        assert result == state.model_dump()

    def test_empty_state_to_dict(self) -> None:
        """Пустой BaseState.to_dict() возвращает пустой словарь."""
        # Arrange
        state = BaseState()

        # Act
        result = state.to_dict()

        # Assert
        assert result == {}
