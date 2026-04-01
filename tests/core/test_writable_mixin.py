# tests/core/test_writable_mixin.py
"""
Тесты WritableMixin — миксин для dict-подобной записи атрибутов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

WritableMixin добавляет dict-подобный интерфейс записи к любому объекту:
__setitem__, __delitem__, write() с контролем разрешённых ключей, update()
для массового обновления. Используется совместно с ReadableMixin.

Наследуется двумя классами ядра:
- BaseState — состояние конвейера аспектов (динамические поля).
- BaseResult — результат действия (pydantic BaseModel, mutable, extra="allow").

НЕ используется в BaseParams (frozen, только чтение) и Context-компонентах
(UserInfo, RequestInfo, RuntimeInfo — dataclass, неизменяемые после создания).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

__setitem__:
    - Создание нового атрибута через obj["key"] = value.
    - Перезапись существующего атрибута.

__delitem__:
    - Удаление существующего атрибута через del obj["key"].
    - KeyError при удалении несуществующего атрибута.

write(key, value, allowed_keys):
    - Запись разрешённого ключа — успешно.
    - Запись запрещённого ключа — KeyError с информативным сообщением.
    - Запись без allowed_keys (None) — любой ключ разрешён.

update(dict):
    - Массовое обновление нескольких атрибутов за один вызов.
    - Перезапись существующих и создание новых.
"""

import pytest

from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# __setitem__ — запись через квадратные скобки
# ═════════════════════════════════════════════════════════════════════════════


class TestSetItem:
    """Запись атрибутов через obj['key'] = value."""

    def test_creates_new_attribute(self) -> None:
        """
        obj["key"] = value создаёт новый атрибут на объекте.

        WritableMixin.__setitem__ делегирует в setattr(self, key, value).
        После записи значение доступно и через точку (obj.key),
        и через квадратные скобки (obj["key"]).
        """
        # Arrange — пустой state без атрибутов
        state = BaseState()

        # Act — запись нового атрибута через dict-подобный интерфейс,
        # WritableMixin.__setitem__ вызывает setattr(self, "count", 42)
        state["count"] = 42

        # Assert — значение доступно через атрибутный доступ (точка)
        assert state.count == 42

        # Assert — значение доступно через dict-подобный доступ (скобки),
        # ReadableMixin.__getitem__ вызывает getattr(self, "count")
        assert state["count"] == 42

    def test_overwrites_existing_attribute(self) -> None:
        """
        Повторная запись по тому же ключу заменяет старое значение.

        setattr на уже существующем атрибуте перезаписывает его.
        Это штатное поведение: аспект может обновить поле state,
        записанное предыдущим аспектом.
        """
        # Arrange — state с начальным значением status="pending"
        state = BaseState({"status": "pending"})

        # Act — перезапись status на новое значение
        state["status"] = "completed"

        # Assert — старое значение "pending" заменено на "completed"
        assert state["status"] == "completed"

    def test_supports_different_value_types(self) -> None:
        """
        Запись поддерживает любые типы значений: строки, числа,
        списки, словари, None, булевы значения.

        BaseState — динамический контейнер без типизации полей.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — запись значений разных типов
        state["string_val"] = "hello"
        state["int_val"] = 42
        state["float_val"] = 3.14
        state["bool_val"] = True
        state["none_val"] = None
        state["list_val"] = [1, 2, 3]
        state["dict_val"] = {"nested": "value"}

        # Assert — все типы записаны и читаются корректно
        assert state["string_val"] == "hello"
        assert state["int_val"] == 42
        assert state["float_val"] == 3.14
        assert state["bool_val"] is True
        assert state["none_val"] is None
        assert state["list_val"] == [1, 2, 3]
        assert state["dict_val"] == {"nested": "value"}


# ═════════════════════════════════════════════════════════════════════════════
# __delitem__ — удаление через del obj["key"]
# ═════════════════════════════════════════════════════════════════════════════


class TestDelItem:
    """Удаление атрибутов через del obj['key']."""

    def test_removes_existing_attribute(self) -> None:
        """
        del obj["key"] удаляет атрибут с объекта.

        WritableMixin.__delitem__ делегирует в delattr(self, key).
        После удаления атрибут больше не доступен ни через точку,
        ни через скобки, ни через оператор in.
        """
        # Arrange — state с временным полем temp
        state = BaseState({"temp": True, "keep": "value"})

        # Act — удаление temp через WritableMixin.__delitem__,
        # который вызывает delattr(self, "temp")
        del state["temp"]

        # Assert — temp удалён, keep остался
        assert "temp" not in state
        assert "keep" in state

    def test_missing_key_raises_key_error(self) -> None:
        """
        del obj["missing"] бросает KeyError для несуществующего ключа.

        WritableMixin.__delitem__ ловит AttributeError от delattr
        и перебрасывает как KeyError — поведение идентично dict.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act & Assert — попытка удалить несуществующий ключ,
        # delattr бросает AttributeError, __delitem__ оборачивает в KeyError
        with pytest.raises(KeyError):
            del state["nonexistent"]


# ═════════════════════════════════════════════════════════════════════════════
# write() — контролируемая запись с валидацией ключей
# ═════════════════════════════════════════════════════════════════════════════


class TestWrite:
    """Контролируемая запись через write(key, value, allowed_keys)."""

    def test_allowed_key_succeeds(self) -> None:
        """
        write("key", value, allowed_keys=["key", ...]) — запись разрешённого
        ключа проходит успешно.

        Метод write предназначен для ситуаций, когда нужно ограничить
        набор полей, доступных для записи: плагины и аспекты могут
        передавать allowed_keys, чтобы предотвратить случайную
        перезапись критичных данных другими компонентами.
        """
        # Arrange — пустой state и список из двух разрешённых ключей
        state = BaseState()
        allowed = ["total", "discount"]

        # Act — запись ключа total, который входит в allowed_keys
        state.write("total", 1500, allowed_keys=allowed)

        # Assert — значение записано, доступно через атрибут
        assert state.total == 1500

    def test_disallowed_key_raises_key_error(self) -> None:
        """
        write("forbidden", value, allowed_keys=[...]) — запись ключа,
        отсутствующего в allowed_keys, бросает KeyError.

        Сообщение об ошибке содержит имя запрещённого ключа
        и полный список разрешённых — для быстрой диагностики.
        """
        # Arrange — пустой state и ограниченный список ключей
        state = BaseState()
        allowed = ["total", "discount"]

        # Act & Assert — попытка записать ключ "secret", которого
        # нет в allowed_keys, бросает KeyError с информативным сообщением
        with pytest.raises(KeyError, match="не входит в список разрешённых"):
            state.write("secret", 42, allowed_keys=allowed)

    def test_without_allowed_keys_permits_any(self) -> None:
        """
        write("key", value) без allowed_keys — любой ключ разрешён.

        Если allowed_keys=None (по умолчанию), валидация отключена.
        Эквивалентно obj["key"] = value.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — запись произвольного ключа без ограничений,
        # allowed_keys=None → проверка пропускается, setattr выполняется
        state.write("anything", "allowed")

        # Assert — значение записано без ошибок
        assert state["anything"] == "allowed"

    def test_write_overwrites_existing_value(self) -> None:
        """
        write() перезаписывает существующее значение, если ключ разрешён.
        """
        # Arrange — state с начальным значением total=100
        state = BaseState({"total": 100})

        # Act — перезапись total на новое значение через write
        state.write("total", 999, allowed_keys=["total"])

        # Assert — значение обновлено
        assert state["total"] == 999


# ═════════════════════════════════════════════════════════════════════════════
# update() — массовое обновление
# ═════════════════════════════════════════════════════════════════════════════


class TestUpdate:
    """Массовое обновление через update(dict)."""

    def test_creates_multiple_attributes(self) -> None:
        """
        update({"a": 1, "b": 2}) создаёт несколько атрибутов за один вызов.

        Удобно для инициализации state из словаря или применения
        пакета изменений от плагина. Внутри update() — цикл
        по парам (key, value) с вызовом setattr для каждой.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — массовая запись двух полей из словаря
        state.update({"a": 1, "b": 2})

        # Assert — оба поля созданы и доступны
        assert state.a == 1
        assert state.b == 2

    def test_overwrites_existing_attributes(self) -> None:
        """
        update() перезаписывает существующие атрибуты и создаёт новые.
        """
        # Arrange — state с начальным значением a=1
        state = BaseState({"a": 1})

        # Act — обновление: a перезаписывается, b создаётся
        state.update({"a": 999, "b": 2})

        # Assert — a обновлён, b создан
        assert state.a == 999
        assert state.b == 2

    def test_empty_dict_changes_nothing(self) -> None:
        """
        update({}) с пустым словарём — state не меняется.
        """
        # Arrange — state с одним полем
        state = BaseState({"total": 100})

        # Act — пустое обновление
        state.update({})

        # Assert — state не изменился
        assert state.to_dict() == {"total": 100}
