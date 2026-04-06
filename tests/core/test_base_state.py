# tests/core/test_base_state.py
"""
Тесты BaseState — frozen-состояние конвейера аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseState — frozen pydantic-модель (наследник BaseSchema) с extra="allow",
хранящая накопленные данные между шагами конвейера аспектов. Каждый
regular-аспект возвращает dict с новыми полями, машина проверяет их
чекерами и создаёт НОВЫЙ BaseState через kwargs:

    new_state = BaseState(**{**old_state.to_dict(), **aspect_result})

Аспект получает state только на чтение — мутация невозможна после создания
(frozen=True).

BaseState наследует BaseSchema (dict-подобное чтение, resolve по dot-path).
Методы записи (__setitem__, __delitem__, write, update) отсутствуют.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - Через kwargs — ключи становятся extra-полями.
    - Пустое создание — начальное состояние перед первым аспектом.

Чтение (BaseSchema):
    - __getitem__, __contains__, get, keys, values, items.
    - resolve для плоских полей и с default для отсутствующих.

Неизменяемость (frozen=True):
    - setattr запрещён (frozen).
    - __setitem__ отсутствует.
    - __delitem__ отсутствует.
    - write и update отсутствуют.

Сериализация:
    - to_dict() / model_dump() возвращает все поля.
    - repr() содержит имя класса и все поля.
"""

import pytest

from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestCreation:
    """Создание BaseState через kwargs и пустое."""

    def test_create_from_dict(self) -> None:
        """
        Словарь при создании — каждый ключ становится extra-полем.

        Машина создаёт BaseState через распаковку kwargs:
        BaseState(**{**old_state.to_dict(), **new_dict}).
        """
        # Arrange — данные, которые мог бы вернуть regular-аспект
        initial = {"txn_id": "TXN-001", "total": 1500.0}

        # Act — создание state через распаковку kwargs
        state = BaseState(**initial)

        # Assert — каждый ключ стал extra-полем, доступным через
        # точку (state.txn_id) и скобки (state["txn_id"])
        assert state.txn_id == "TXN-001"
        assert state.total == 1500.0

    def test_create_empty(self) -> None:
        """
        Пустой state — начальное состояние перед первым regular-аспектом.
        Машина создаёт BaseState() в начале _execute_regular_aspects().
        """
        # Arrange & Act — создание начального пустого state
        state = BaseState()

        # Assert — пустой словарь
        assert state.to_dict() == {}

    def test_create_with_kwargs(self) -> None:
        """
        BaseState принимает kwargs напрямую.
        """
        # Arrange & Act
        state = BaseState(a=1, b="two", c=True)

        # Assert
        assert state["a"] == 1
        assert state["b"] == "two"
        assert state["c"] is True


# ═════════════════════════════════════════════════════════════════════════════
# Чтение через BaseSchema
# ═════════════════════════════════════════════════════════════════════════════


class TestReadAccess:
    """Dict-подобное чтение атрибутов BaseState через BaseSchema."""

    def test_getitem_returns_value(self) -> None:
        """
        state["key"] — основной способ чтения данных в аспектах.
        """
        # Arrange — state с одним полем amount
        state = BaseState(amount=500)

        # Act — чтение через квадратные скобки
        result = state["amount"]

        # Assert
        assert result == 500

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        Обращение к несуществующему ключу — KeyError.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act & Assert
        with pytest.raises(KeyError):
            _ = state["missing"]

    def test_contains_checks_key_existence(self) -> None:
        """
        Оператор 'in' проверяет наличие ключа в state.
        """
        # Arrange — state с одним ключом total
        state = BaseState(total=100)

        # Act & Assert
        assert "total" in state
        assert "missing" not in state

    def test_get_returns_value_or_default(self) -> None:
        """
        state.get("key", default) — безопасное чтение без KeyError.
        """
        # Arrange — state с одним ключом total
        state = BaseState(total=100)

        # Act & Assert — существующий ключ
        assert state.get("total") == 100
        # Act & Assert — отсутствующий ключ с default
        assert state.get("missing", "fallback") == "fallback"
        # Act & Assert — отсутствующий ключ без default → None
        assert state.get("missing") is None

    def test_keys_values_items(self) -> None:
        """
        keys(), values(), items() — итерация по содержимому state.
        """
        # Arrange — state с двумя полями
        state = BaseState(a=1, b=2)

        # Act
        keys = state.keys()
        values = state.values()
        items = state.items()

        # Assert — содержит оба поля
        assert sorted(keys) == ["a", "b"]
        assert sorted(values) == [1, 2]
        assert sorted(items) == [("a", 1), ("b", 2)]

    def test_resolve_flat_field(self) -> None:
        """
        resolve("key") — прямой доступ к плоскому полю.
        Используется в шаблонах логирования: {%state.total}
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = state.resolve("total")

        # Assert
        assert result == 1500

    def test_resolve_missing_returns_none(self) -> None:
        """
        resolve("missing") без default возвращает None.
        """
        # Arrange
        state = BaseState(total=1500)

        # Act
        result = state.resolve("missing")

        # Assert
        assert result is None

    def test_resolve_missing_with_explicit_default(self) -> None:
        """
        resolve("missing", default="N/A") возвращает "N/A".
        """
        # Arrange — свежий state
        state = BaseState(total=1500)

        # Act
        result = state.resolve("missing", default="N/A")

        # Assert
        assert result == "N/A"


# ═════════════════════════════════════════════════════════════════════════════
# Неизменяемость (frozen)
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """BaseState полностью неизменяем после создания (frozen=True)."""

    def test_setattr_raises(self) -> None:
        """
        Прямая запись атрибута через точку запрещена.
        Pydantic frozen=True бросает ValidationError при попытке записи.
        """
        # Arrange — state с начальным значением
        state = BaseState(value=1)

        # Act & Assert — попытка изменить существующий атрибут
        with pytest.raises(Exception):
            state.value = 2

    def test_setattr_new_key_raises(self) -> None:
        """
        Добавление нового атрибута запрещено.
        Pydantic frozen=True бросает ValidationError.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act & Assert — попытка добавить новый атрибут
        with pytest.raises(Exception):
            state.new_key = "value"

    def test_delattr_raises(self) -> None:
        """
        Удаление атрибута запрещено.
        """
        # Arrange — state с полем для удаления
        state = BaseState(to_delete="value")

        # Act & Assert
        with pytest.raises(Exception):
            del state.to_delete

    def test_setitem_raises(self) -> None:
        """
        Dict-подобная запись через [] отсутствует.
        BaseState не определяет __setitem__.
        """
        # Arrange — state с существующим ключом
        state = BaseState(key="old")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            state["key"] = "new"

    def test_delitem_raises(self) -> None:
        """
        Dict-подобное удаление через del [] отсутствует.
        """
        # Arrange — state с ключом
        state = BaseState(key="value")

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            del state["key"]

    def test_write_method_missing(self) -> None:
        """Метод write() отсутствует."""
        state = BaseState()
        assert not hasattr(state, "write")

    def test_update_method_missing(self) -> None:
        """Метод update() отсутствует."""
        state = BaseState()
        assert not hasattr(state, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Сериализация
# ═════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Сериализация BaseState: to_dict(), model_dump() и repr()."""

    def test_to_dict_returns_all_fields(self) -> None:
        """
        to_dict() возвращает словарь всех extra-полей.
        Эквивалентен model_dump(). Используется для передачи в плагины
        через state_aspect в PluginEvent и для логирования.
        """
        # Arrange — state с двумя полями
        state = BaseState(a=1, b=2)

        # Act
        result = state.to_dict()

        # Assert
        assert result == {"a": 1, "b": 2}

    def test_to_dict_matches_model_dump(self) -> None:
        """
        to_dict() эквивалентен model_dump().
        """
        # Arrange
        state = BaseState(total=100)
        state.resolve("total")  # вызов resolve не влияет на to_dict

        # Act
        result = state.to_dict()

        # Assert — совпадает с model_dump
        assert result == state.model_dump()
        assert result == {"total": 100}

    def test_repr_contains_class_name_and_fields(self) -> None:
        """
        repr() возвращает строку вида "BaseState(key1=value1, key2=value2)".
        """
        # Arrange — state с одним полем
        state = BaseState(total=1500)

        # Act
        result = repr(state)

        # Assert — содержит имя класса и поле
        assert "BaseState" in result
        assert "total" in result
        assert "1500" in result

    def test_repr_empty_state(self) -> None:
        """
        repr() пустого state — "BaseState()".
        """
        # Arrange & Act
        state = BaseState()

        # Act
        result = repr(state)

        # Assert
        assert result == "BaseState()"
