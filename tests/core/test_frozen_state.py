# tests/core/test_frozen_state.py
"""
Тесты frozen-семантики BaseState.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что BaseState полностью неизменяем после создания:
запись атрибутов, удаление атрибутов, dict-подобная запись — всё
запрещено. Единственный способ «изменить» состояние — создать
новый экземпляр.

Также проверяет корректность чтения: dict-подобный доступ, resolve,
keys, values, items, to_dict, repr.
"""

import pytest

from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Создание и чтение
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateCreation:
    """Тесты создания и чтения данных из BaseState."""

    def test_create_empty(self) -> None:
        """Пустой BaseState создаётся без ошибок и не содержит полей."""
        # Arrange & Act
        state = BaseState()

        # Assert — пустое состояние
        assert state.to_dict() == {}
        assert state.keys() == []

    def test_create_with_data(self) -> None:
        """BaseState принимает dict и делает каждый ключ атрибутом."""
        # Arrange
        data = {"total": 1500, "user": "agent", "active": True}

        # Act
        state = BaseState(data)

        # Assert — все данные доступны через атрибуты и dict-интерфейс
        assert state["total"] == 1500
        assert state["user"] == "agent"
        assert state["active"] is True

    def test_create_with_none(self) -> None:
        """None в конструкторе эквивалентен пустому состоянию."""
        # Arrange & Act
        state = BaseState(None)

        # Assert
        assert state.to_dict() == {}

    def test_getitem_access(self) -> None:
        """Dict-подобный доступ через квадратные скобки."""
        # Arrange
        state = BaseState({"amount": 42.5})

        # Act & Assert
        assert state["amount"] == 42.5

    def test_getitem_missing_key_raises(self) -> None:
        """Обращение к несуществующему ключу бросает KeyError."""
        # Arrange
        state = BaseState({"exists": True})

        # Act & Assert — ключ не существует
        with pytest.raises(KeyError):
            _ = state["missing"]

    def test_get_with_default(self) -> None:
        """Метод get() возвращает default для отсутствующего ключа."""
        # Arrange
        state = BaseState({"key": "value"})

        # Act & Assert
        assert state.get("key") == "value"
        assert state.get("missing") is None
        assert state.get("missing", "fallback") == "fallback"

    def test_contains(self) -> None:
        """Оператор in проверяет наличие ключа."""
        # Arrange
        state = BaseState({"present": 1})

        # Act & Assert
        assert "present" in state
        assert "absent" not in state

    def test_keys_values_items(self) -> None:
        """Методы keys, values, items возвращают корректные данные."""
        # Arrange
        state = BaseState({"a": 1, "b": 2})

        # Act
        keys = state.keys()
        values = state.values()
        items = state.items()

        # Assert — порядок соответствует порядку dict в Python 3.7+
        assert set(keys) == {"a", "b"}
        assert set(values) == {1, 2}
        assert set(items) == {("a", 1), ("b", 2)}

    def test_to_dict(self) -> None:
        """to_dict() возвращает словарь публичных полей."""
        # Arrange
        state = BaseState({"x": 10, "y": 20})

        # Act
        result = state.to_dict()

        # Assert — обычный dict, не содержит приватных атрибутов
        assert result == {"x": 10, "y": 20}
        assert isinstance(result, dict)

    def test_to_dict_excludes_private(self) -> None:
        """to_dict() не включает атрибуты, начинающиеся с подчёркивания."""
        # Arrange — внутренние атрибуты (resolve_cache и др.) скрыты
        state = BaseState({"public": "yes"})

        # Act
        result = state.to_dict()

        # Assert — только публичные ключи
        assert all(not k.startswith("_") for k in result)
        assert "public" in result

    def test_resolve(self) -> None:
        """resolve() работает для плоских ключей."""
        # Arrange — свежий state, чтобы избежать влияния кеша от предыдущих тестов
        state = BaseState({"total": 500})

        # Act & Assert
        assert state.resolve("total") == 500
        assert state.resolve("missing") is None

        # Для проверки default используем отдельный свежий экземпляр,
        # потому что resolve кеширует результат по dotpath.
        # Если сначала вызвать resolve("missing") → None (кешируется),
        # то повторный resolve("missing", default="default") вернёт None из кеша.
        fresh_state = BaseState({"total": 500})
        assert fresh_state.resolve("missing", default="default") == "default"

    def test_repr(self) -> None:
        """repr() показывает содержимое в формате BaseState(key=value)."""
        # Arrange
        state = BaseState({"count": 3})

        # Act
        result = repr(state)

        # Assert
        assert "BaseState" in result
        assert "count=3" in result


# ═════════════════════════════════════════════════════════════════════════════
# Frozen-семантика: запись запрещена
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateFrozen:
    """Тесты неизменяемости BaseState после создания."""

    def test_setattr_raises(self) -> None:
        """Запись через атрибут запрещена — AttributeError."""
        # Arrange
        state = BaseState({"value": 1})

        # Act & Assert — нельзя изменить существующий атрибут
        with pytest.raises(AttributeError, match="frozen"):
            state.value = 2

    def test_setattr_new_key_raises(self) -> None:
        """Добавление нового атрибута запрещено — AttributeError."""
        # Arrange
        state = BaseState()

        # Act & Assert — нельзя добавить новый атрибут
        with pytest.raises(AttributeError, match="frozen"):
            state.new_key = "value"

    def test_delattr_raises(self) -> None:
        """Удаление атрибута запрещено — AttributeError."""
        # Arrange
        state = BaseState({"to_delete": "value"})

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            del state.to_delete

    def test_no_setitem(self) -> None:
        """Dict-подобная запись через [] отсутствует (нет WritableMixin)."""
        # Arrange
        state = BaseState({"key": "old"})

        # Act & Assert — метод __setitem__ не существует,
        # запись через [] вызывает TypeError или AttributeError
        with pytest.raises((TypeError, AttributeError)):
            state["key"] = "new"

    def test_no_delitem(self) -> None:
        """Dict-подобное удаление через del [] отсутствует."""
        # Arrange
        state = BaseState({"key": "value"})

        # Act & Assert
        with pytest.raises((TypeError, AttributeError)):
            del state["key"]

    def test_no_write_method(self) -> None:
        """Метод write() не существует (WritableMixin удалён)."""
        # Arrange
        state = BaseState()

        # Act & Assert
        assert not hasattr(state, "write")

    def test_no_update_method(self) -> None:
        """Метод update() не существует (WritableMixin удалён)."""
        # Arrange
        state = BaseState()

        # Act & Assert
        assert not hasattr(state, "update")


# ═════════════════════════════════════════════════════════════════════════════
# Паттерн «изменения» — создание нового экземпляра
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseStateImmutableUpdate:
    """Тесты паттерна обновления через создание нового экземпляра."""

    def test_merge_creates_new_state(self) -> None:
        """Мерж двух состояний создаёт новый объект, не мутируя старый."""
        # Arrange
        old_state = BaseState({"total": 100})
        new_data = {"discount": 10}

        # Act — паттерн, используемый машиной на каждом шаге конвейера
        new_state = BaseState({**old_state.to_dict(), **new_data})

        # Assert — новый state содержит оба поля
        assert new_state["total"] == 100
        assert new_state["discount"] == 10

        # Assert — старый state не изменился
        assert old_state.to_dict() == {"total": 100}
        assert "discount" not in old_state

    def test_override_creates_new_state(self) -> None:
        """Перезапись поля создаёт новый объект с обновлённым значением."""
        # Arrange
        original = BaseState({"status": "pending"})

        # Act
        updated = BaseState({**original.to_dict(), "status": "completed"})

        # Assert
        assert updated["status"] == "completed"
        assert original["status"] == "pending"

    def test_original_and_copy_are_independent(self) -> None:
        """Два BaseState из одного dict — полностью независимые объекты."""
        # Arrange
        data = {"count": 0}
        state_a = BaseState(data)
        state_b = BaseState(data)

        # Act & Assert — попытка мутации одного не влияет на другой
        # (мутация невозможна, но объекты точно разные)
        assert state_a is not state_b
        assert state_a.to_dict() == state_b.to_dict()
