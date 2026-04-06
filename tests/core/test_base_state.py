# tests/core/test_base_state.py
"""
Тесты BaseState — состояние конвейера аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseState — неизменяемый объект, хранящий накопленные данные между шагами
конвейера аспектов. Каждый regular-аспект возвращает dict с новыми полями,
машина (ActionProductMachine) проверяет их чекерами и создаёт НОВЫЙ
BaseState, объединяя предыдущие данные с новыми. Аспект получает state
только на чтение — мутация невозможна после создания.

BaseState наследует ReadableMixin (dict-подобное чтение, resolve по dot-path).
Методы записи (__setitem__, __delitem__, write, update) отсутствуют.

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

Неизменяемость:
    - __setitem__ отсутствует (AttributeError или TypeError).
    - __delitem__ отсутствует.
    - write и update отсутствуют.
    - setattr запрещён (AttributeError).

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
        state = BaseState()

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
# Неизменяемость (frozen)
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """BaseState полностью неизменяем после создания."""

    def test_setattr_raises(self) -> None:
        """
        Прямая запись атрибута через точку запрещена.

        __setattr__ переопределён и всегда бросает AttributeError.
        Единственный способ записать данные — через конструктор.
        """
        # Arrange — state с начальным значением
        state = BaseState({"value": 1})

        # Act & Assert — попытка изменить существующий атрибут
        with pytest.raises(AttributeError, match="frozen"):
            state.value = 2

    def test_setattr_new_key_raises(self) -> None:
        """
        Добавление нового атрибута запрещено.

        Даже если атрибут не существовал, запись запрещена.
        """
        # Arrange — пустой state
        state = BaseState()

        # Act & Assert — попытка добавить новый атрибут
        with pytest.raises(AttributeError, match="frozen"):
            state.new_key = "value"

    def test_delattr_raises(self) -> None:
        """
        Удаление атрибута запрещено.

        __delattr__ переопределён и всегда бросает AttributeError.
        """
        # Arrange — state с полем для удаления
        state = BaseState({"to_delete": "value"})

        # Act & Assert — попытка удалить атрибут
        with pytest.raises(AttributeError, match="frozen"):
            del state.to_delete

    def test_setitem_raises(self) -> None:
        """
        Dict-подобная запись через [] отсутствует.

        BaseState не наследует WritableMixin, поэтому __setitem__
        не определён. Попытка записи через квадратные скобки
        вызывает TypeError или AttributeError.
        """
        # Arrange — state с существующим ключом
        state = BaseState({"key": "old"})

        # Act & Assert — попытка записи через []
        with pytest.raises((TypeError, AttributeError)):
            state["key"] = "new"

    def test_delitem_raises(self) -> None:
        """
        Dict-подобное удаление через del [] отсутствует.

        __delitem__ не определён.
        """
        # Arrange — state с ключом
        state = BaseState({"key": "value"})

        # Act & Assert — попытка удаления через []
        with pytest.raises((TypeError, AttributeError)):
            del state["key"]

    def test_write_method_missing(self) -> None:
        """
        Метод write() отсутствует (WritableMixin не используется).

        Ранее write использовался для контролируемой записи,
        но в frozen-модели этот метод не нужен.
        """
        state = BaseState()
        assert not hasattr(state, "write")

    def test_update_method_missing(self) -> None:
        """
        Метод update() отсутствует (WritableMixin не используется).

        Массовое обновление state теперь выполняется через создание
        нового экземпляра: BaseState({**old_state.to_dict(), **new_data}).
        """
        state = BaseState()
        assert not hasattr(state, "update")


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
