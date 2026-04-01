# tests/core/test_base_state.py
"""
Тесты BaseState — состояние конвейера аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseState — мутабельный контейнер данных, накапливаемых regular-аспектами
в ходе выполнения конвейера ActionProductMachine. Каждый regular-аспект
возвращает dict, который машина мержит в текущий state. Summary-аспект
читает накопленные данные из state и формирует Result.

BaseState наследует ReadableMixin (dict-подобное чтение, resolve по dot-path)
и WritableMixin (dict-подобная запись, write с allowed_keys, update).
Это НЕ pydantic-модель — это лёгкий контейнер с динамическими полями,
аналог dict с атрибутным доступом.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Создание:
    - Из словаря — ключи становятся атрибутами.
    - Пустое создание — начальное состояние перед первым аспектом.
    - None как аргумент — эквивалентно пустому state.

Чтение (ReadableMixin):
    - __getitem__, __contains__, get, keys, values, items.
    - resolve для плоских полей и с default для отсутствующих.

Запись (WritableMixin):
    - __setitem__ создаёт и перезаписывает атрибуты.
    - __delitem__ удаляет атрибуты, KeyError для отсутствующих.
    - write с allowed_keys — контролируемая запись.
    - update — массовое обновление из словаря.

Сериализация:
    - to_dict() возвращает только публичные поля, без приватных.
    - repr() содержит имя класса и все поля.
"""

import pytest

from action_machine.core.base_state import BaseState

# ═════════════════════════════════════════════════════════════════════════════
# Создание и инициализация
# ═════════════════════════════════════════════════════════════════════════════


class TestCreation:
    """Создание BaseState из словаря, пустое и с None."""

    def test_create_from_dict(self) -> None:
        """
        Словарь при создании — каждый ключ становится атрибутом.

        Так state заполняется в машине: ActionProductMachine берёт dict
        от regular-аспекта и создаёт BaseState({**old_state, **new_dict}).
        """
        # Arrange — данные, которые мог бы вернуть regular-аспект
        # process_payment: {"txn_id": "TXN-001", "total": 1500.0}
        initial = {"txn_id": "TXN-001", "total": 1500.0}

        # Act — создание state как делает машина после мержа
        # результата regular-аспекта с предыдущим state
        state = BaseState(initial)

        # Assert — каждый ключ словаря стал атрибутом объекта,
        # доступным и через точку (state.txn_id) и через скобки (state["txn_id"])
        assert state.txn_id == "TXN-001"
        assert state.total == 1500.0

    def test_create_empty(self) -> None:
        """
        Пустой state — начальное состояние перед первым regular-аспектом.

        Машина создаёт BaseState() в начале _execute_regular_aspects().
        Первый аспект получает пустой state и записывает в него данные.
        """
        # Arrange & Act — создание начального пустого state,
        # как это делает машина перед запуском конвейера аспектов
        state = BaseState()

        # Assert — пустой словарь, ни одного публичного атрибута,
        # to_dict() фильтрует приватные (начинающиеся с '_')
        assert state.to_dict() == {}

    def test_create_with_none(self) -> None:
        """
        None как аргумент — эквивалентно пустому state.

        Защитное поведение: если кто-то передаст None вместо словаря,
        state будет пустым, а не упадёт с TypeError.
        """
        # Arrange & Act — None вместо словаря, конструктор
        # проверяет truthiness: if initial: ... — None не проходит
        state = BaseState(None)

        # Assert — state пустой, как при создании без аргументов
        assert state.to_dict() == {}


# ═════════════════════════════════════════════════════════════════════════════
# Чтение через ReadableMixin
# ═════════════════════════════════════════════════════════════════════════════


class TestReadAccess:
    """Dict-подобное чтение атрибутов BaseState через ReadableMixin."""

    def test_getitem_returns_value(self) -> None:
        """
        state["key"] — основной способ чтения данных в аспектах.

        Summary-аспект читает данные, накопленные regular-аспектами:
        order_id = state["txn_id"]
        """
        # Arrange — state с одним полем amount, записанным regular-аспектом
        state = BaseState({"amount": 500})

        # Act — чтение через квадратные скобки, как у обычного dict
        result = state["amount"]

        # Assert — значение извлечено корректно
        assert result == 500

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        Обращение к несуществующему ключу — KeyError.

        Это поведение идентично dict: если regular-аспект не записал
        ожидаемое поле, summary-аспект получит KeyError при попытке
        прочитать его.
        """
        # Arrange — пустой state, ни один аспект ещё не записал данные
        state = BaseState()

        # Act & Assert — попытка прочитать несуществующий ключ,
        # ReadableMixin.__getitem__ ловит AttributeError и бросает KeyError
        with pytest.raises(KeyError):
            _ = state["missing"]

    def test_contains_checks_key_existence(self) -> None:
        """
        Оператор 'in' проверяет наличие ключа в state.

        Используется в аспектах для условной логики:
        if "discount" in state: total -= state["discount"]
        """
        # Arrange — state с одним ключом total
        state = BaseState({"total": 100})

        # Act & Assert — total присутствует, missing отсутствует.
        # ReadableMixin.__contains__ делегирует в hasattr(self, key)
        assert "total" in state
        assert "missing" not in state

    def test_get_returns_value_or_default(self) -> None:
        """
        state.get("key", default) — безопасное чтение без KeyError.

        Аналог dict.get(): возвращает значение если ключ есть,
        иначе default (по умолчанию None).
        """
        # Arrange — state с одним ключом total
        state = BaseState({"total": 100})

        # Act & Assert — существующий ключ возвращает своё значение
        assert state.get("total") == 100

        # Act & Assert — отсутствующий ключ с явным default
        assert state.get("missing", "fallback") == "fallback"

        # Act & Assert — отсутствующий ключ без default → None
        assert state.get("missing") is None

    def test_keys_values_items(self) -> None:
        """
        keys(), values(), items() — итерация по содержимому state.

        Используется для логирования, сериализации и передачи
        в плагины через state.to_dict() → state_aspect в PluginEvent.
        """
        # Arrange — state с двумя полями
        state = BaseState({"a": 1, "b": 2})

        # Act — получение списков ключей, значений и пар
        keys = state.keys()
        values = state.values()
        items = state.items()

        # Assert — содержит оба поля. Сортировка для детерминированного
        # сравнения, т.к. порядок атрибутов не гарантирован
        assert sorted(keys) == ["a", "b"]
        assert sorted(values) == [1, 2]
        assert sorted(items) == [("a", 1), ("b", 2)]

    def test_resolve_flat_field(self) -> None:
        """
        resolve("key") — прямой доступ к плоскому полю.

        Эквивалентно state["key"], но не бросает KeyError при отсутствии.
        Используется в шаблонах логирования: {%state.total}
        """
        # Arrange — state с полем total, записанным аспектом calc_total
        state = BaseState({"total": 1500})

        # Act — resolve по одному сегменту пути,
        # ReadableMixin.resolve разбивает "total" по точкам → ["total"],
        # затем вызывает _resolve_one_step(state, "total")
        result = state.resolve("total")

        # Assert — значение 1500 извлечено из атрибута state.total
        assert result == 1500

    def test_resolve_missing_returns_none(self) -> None:
        """
        resolve("missing") без default возвращает None.

        _resolve_one_step вернул _SENTINEL для "missing",
        цикл прерывается, default=None записывается в кеш
        и возвращается.
        """
        # Arrange — state с полем total, но без поля missing
        state = BaseState({"total": 1500})

        # Act — resolve без default
        result = state.resolve("missing")

        # Assert — None как default по умолчанию
        assert result is None

    def test_resolve_missing_with_explicit_default(self) -> None:
        """
        resolve("missing", default="N/A") возвращает "N/A".

        Используется отдельный экземпляр state, потому что resolve
        кеширует результат по dotpath. Если бы сначала вызвать
        resolve("missing") → None (записывается в кеш), то повторный
        resolve("missing", default="N/A") вернул бы None из кеша,
        а не "N/A". Это документированное поведение кеша, покрытое
        в test_resolve_caching.py::TestCacheDefault.
        """
        # Arrange — свежий state без кеша для ключа "missing"
        state = BaseState({"total": 1500})

        # Act — resolve с явным default на чистом экземпляре
        result = state.resolve("missing", default="N/A")

        # Assert — возвращён переданный default
        assert result == "N/A"


# ═════════════════════════════════════════════════════════════════════════════
# Запись через WritableMixin
# ═════════════════════════════════════════════════════════════════════════════


class TestWriteAccess:
    """Dict-подобная запись атрибутов BaseState через WritableMixin."""

    def test_setitem_creates_new_attribute(self) -> None:
        """
        state["key"] = value — создание нового атрибута.

        Аспекты могут динамически добавлять поля в state
        через dict-подобный интерфейс.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — запись нового ключа через WritableMixin.__setitem__,
        # который делегирует в setattr(self, "count", 42)
        state["count"] = 42

        # Assert — значение доступно и через точку, и через скобки
        assert state.count == 42
        assert state["count"] == 42

    def test_setitem_overwrites_existing(self) -> None:
        """
        Повторная запись по тому же ключу — перезапись значения.
        """
        # Arrange — state с начальным значением status
        state = BaseState({"status": "pending"})

        # Act — перезапись существующего атрибута
        state["status"] = "completed"

        # Assert — старое значение заменено новым
        assert state["status"] == "completed"

    def test_delitem_removes_attribute(self) -> None:
        """
        del state["key"] — удаление атрибута. KeyError если ключа нет.
        """
        # Arrange — state с временным полем temp
        state = BaseState({"temp": True})

        # Act — удаление через WritableMixin.__delitem__,
        # который делегирует в delattr(self, "temp")
        del state["temp"]

        # Assert — ключ удалён, больше не доступен
        assert "temp" not in state

        # Act & Assert — удаление несуществующего ключа бросает KeyError,
        # WritableMixin.__delitem__ ловит AttributeError и бросает KeyError
        with pytest.raises(KeyError):
            del state["missing"]

    def test_write_with_allowed_keys(self) -> None:
        """
        write(key, value, allowed_keys) — контролируемая запись.

        Позволяет ограничить набор полей, которые можно изменить.
        Если ключ не в allowed_keys — KeyError. Это защита от
        случайной перезаписи критичных данных в плагинах и аспектах.
        """
        # Arrange — пустой state и список разрешённых ключей
        state = BaseState()
        allowed = ["total", "discount"]

        # Act — запись разрешённого ключа total
        state.write("total", 1500, allowed_keys=allowed)

        # Assert — значение записано успешно
        assert state.total == 1500

        # Act & Assert — запись запрещённого ключа secret бросает KeyError
        # с сообщением, содержащим список разрешённых ключей
        with pytest.raises(KeyError, match="не входит в список разрешённых"):
            state.write("secret", 42, allowed_keys=allowed)

    def test_write_without_allowed_keys(self) -> None:
        """
        write(key, value) без allowed_keys — запись любого ключа.

        Если allowed_keys не передан (None), валидация отключена.
        Эквивалентно state["key"] = value.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — запись без ограничений
        state.write("anything", "allowed")

        # Assert — значение записано
        assert state["anything"] == "allowed"

    def test_update_mass_assignment(self) -> None:
        """
        update(dict) — массовое обновление нескольких полей за один вызов.

        Удобно для инициализации state из словаря или применения
        пакета изменений от плагина.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act — массовое обновление, каждая пара (key, value) записывается
        # через setattr внутри WritableMixin.update()
        state.update({"a": 1, "b": 2})

        # Assert — оба поля записаны
        assert state.a == 1
        assert state.b == 2


# ═════════════════════════════════════════════════════════════════════════════
# Сериализация
# ═════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Сериализация BaseState: to_dict() и repr()."""

    def test_to_dict_returns_public_fields_only(self) -> None:
        """
        to_dict() возвращает словарь только из публичных атрибутов.

        Приватные атрибуты (начинающиеся с '_'), такие как _resolve_cache,
        исключаются. Результат используется для передачи в плагины
        через state_aspect в PluginEvent и для логирования.
        """
        # Arrange — state с двумя публичными полями
        state = BaseState({"a": 1, "b": 2})

        # Act — сериализация в словарь, vars(self) фильтруется
        # по условию not k.startswith('_')
        result = state.to_dict()

        # Assert — только публичные поля, без _resolve_cache и прочих
        assert result == {"a": 1, "b": 2}

    def test_to_dict_excludes_resolve_cache(self) -> None:
        """
        to_dict() не включает _resolve_cache, созданный при вызове resolve().

        _resolve_cache — приватный атрибут, начинается с '_',
        поэтому фильтруется в to_dict().
        """
        # Arrange — state с полем total, затем вызов resolve
        # для заполнения _resolve_cache
        state = BaseState({"total": 100})
        state.resolve("total")

        # Act — сериализация
        result = state.to_dict()

        # Assert — только total, без _resolve_cache
        assert result == {"total": 100}
        assert "_resolve_cache" not in result

    def test_repr_contains_class_name_and_fields(self) -> None:
        """
        repr() возвращает строку вида "BaseState(key1=value1, key2=value2)".

        Используется для отладки в IDE и pytest-выводе при падении тестов.
        """
        # Arrange — state с одним полем
        state = BaseState({"total": 1500})

        # Act — строковое представление
        result = repr(state)

        # Assert — содержит имя класса и поле с значением
        assert "BaseState" in result
        assert "total" in result
        assert "1500" in result

    def test_repr_empty_state(self) -> None:
        """
        repr() пустого state — "BaseState()".
        """
        # Arrange & Act
        state = BaseState()

        # Act — строковое представление пустого объекта
        result = repr(state)

        # Assert — имя класса с пустыми скобками
        assert result == "BaseState()"
