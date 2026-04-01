# tests2/core/test_readable_mixin.py
"""
Тесты ReadableMixin — миксин для dict-подобного чтения атрибутов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ReadableMixin обеспечивает dict-подобный доступ к полям любого объекта:
dataclass, pydantic BaseModel, обычного класса. Наследуется всеми
ключевыми компонентами системы:

- BaseParams — входные параметры действия (pydantic, frozen).
- BaseResult — результат действия (pydantic, mutable, extra).
- BaseState — состояние конвейера (динамические поля).
- Context, UserInfo, RequestInfo, RuntimeInfo — контекст выполнения.
- LogScope — scope логирования.

Обеспечивает два уровня доступа:
1. Плоский — __getitem__, get, __contains__, keys, values, items.
2. Dot-path — resolve("user.roles") обходит вложенные объекты.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Плоский доступ:
    - keys() возвращает только публичные поля (без '_'-префикса).
    - values() возвращает значения публичных полей.
    - items() возвращает пары (ключ, значение) для публичных полей.
    - __getitem__ возвращает значение, KeyError для отсутствующих.
    - __contains__ проверяет наличие атрибута.
    - get() возвращает значение или default.

Приватные атрибуты:
    - keys/values/items исключают атрибуты с '_'-префиксом.
    - _resolve_cache, __mangled и другие приватные не попадают в вывод.

Совместимость с pydantic BaseModel:
    - keys() для pydantic-модели возвращает model_fields + extra-поля.
    - Внутренние pydantic-атрибуты (__pydantic_fields_set__ и т.д.)
      не попадают в keys/values/items.

Совместимость с обычными классами:
    - keys() для обычного класса возвращает публичные атрибуты из vars().
"""

import pytest

from action_machine.core.base_result import BaseResult
from action_machine.core.readable_mixin import ReadableMixin

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class SimpleReadable(ReadableMixin):
    """
    Простой класс с ReadableMixin для тестирования.

    Имитирует объект с произвольными атрибутами — аналог BaseState,
    но без WritableMixin. Используется для изолированного тестирования
    ReadableMixin без влияния pydantic или dataclass.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ReadableWithPrivate(ReadableMixin):
    """
    Класс с публичными и приватными атрибутами для тестирования фильтрации.

    ReadableMixin.keys() должен возвращать только публичные атрибуты.
    Приватные (_private) и mangled (__mangled) должны быть скрыты.
    """

    def __init__(self):
        self.public = "visible"
        self._private = "hidden"
        self.__mangled = "also_hidden"


# ═════════════════════════════════════════════════════════════════════════════
# Плоский доступ: keys, values, items
# ═════════════════════════════════════════════════════════════════════════════


class TestKeysValuesItems:
    """Тесты keys(), values(), items() — итерация по публичным полям."""

    def test_keys_returns_public_attributes(self) -> None:
        """
        keys() возвращает список имён только публичных атрибутов.

        Для обычных классов ReadableMixin использует vars(self)
        и фильтрует атрибуты, начинающиеся с '_'. Это исключает
        приватные поля, _resolve_cache и mangled-атрибуты.
        """
        # Arrange — объект с тремя публичными полями
        obj = SimpleReadable(name="test", value=42, active=True)

        # Act — получение списка ключей через ReadableMixin._get_field_names(),
        # который для не-pydantic объектов возвращает
        # [k for k in vars(self) if not k.startswith("_")]
        keys = obj.keys()

        # Assert — все три публичных атрибута присутствуют, порядок не гарантирован
        assert sorted(keys) == ["active", "name", "value"]

    def test_keys_excludes_private_attributes(self) -> None:
        """
        keys() не включает атрибуты с '_'-префиксом.

        _private и __mangled (который Python превращает в
        _ReadableWithPrivate__mangled) — оба начинаются с '_'
        и фильтруются. Только public остаётся.
        """
        # Arrange — объект с одним публичным и двумя приватными атрибутами
        obj = ReadableWithPrivate()

        # Act — получение ключей с фильтрацией приватных
        keys = obj.keys()

        # Assert — только публичный атрибут в списке
        assert keys == ["public"]
        assert "_private" not in keys
        assert "__mangled" not in keys

    def test_values_returns_public_values_only(self) -> None:
        """
        values() возвращает значения только публичных полей.

        Порядок соответствует порядку keys(). Приватные атрибуты
        исключены — их значения не попадают в результат.
        """
        # Arrange — объект с одним публичным полем
        obj = ReadableWithPrivate()

        # Act — значения через ReadableMixin.values(),
        # который вызывает getattr(self, k) для каждого k из _get_field_names()
        values = obj.values()

        # Assert — только значение публичного атрибута
        assert values == ["visible"]

    def test_items_returns_public_pairs_only(self) -> None:
        """
        items() возвращает пары (ключ, значение) для публичных полей.

        Аналог dict.items(). Используется для итерации по содержимому
        объекта, например при сериализации в лог.
        """
        # Arrange — объект с одним публичным полем
        obj = ReadableWithPrivate()

        # Act — пары через ReadableMixin.items()
        items = obj.items()

        # Assert — только публичная пара
        assert items == [("public", "visible")]

    def test_keys_for_pydantic_model(self) -> None:
        """
        keys() для pydantic BaseModel возвращает поля из model_fields.

        ReadableMixin._get_field_names() определяет тип объекта через
        isinstance(self, BaseModel). Для pydantic-моделей список полей
        берётся из type(self).model_fields.keys(), а не из vars(self).
        Это исключает внутренние pydantic-атрибуты.
        """
        # Arrange — BaseState — не pydantic, BaseResult — pydantic.
        # Используем BaseResult для проверки pydantic-ветки
        result = BaseResult()

        # Act — получение ключей для пустой pydantic-модели
        keys = result.keys()

        # Assert — у пустого BaseResult нет объявленных полей
        assert keys == []

    def test_keys_for_pydantic_with_extra_fields(self) -> None:
        """
        keys() для pydantic с extra="allow" возвращает и объявленные,
        и динамические extra-поля.

        BaseResult использует ConfigDict(extra="allow"), что позволяет
        записывать произвольные поля через result["key"] = value.
        ReadableMixin._get_field_names() объединяет model_fields.keys()
        и __pydantic_extra__.keys() для полного списка.
        """
        # Arrange — BaseResult с динамическим extra-полем
        result = BaseResult()
        result["debug_info"] = "extra data"

        # Act — ключи включают и объявленные поля, и extra
        keys = result.keys()

        # Assert — динамическое поле debug_info присутствует в списке
        assert "debug_info" in keys


# ═════════════════════════════════════════════════════════════════════════════
# Плоский доступ: __getitem__, __contains__, get
# ═════════════════════════════════════════════════════════════════════════════


class TestDictAccess:
    """Тесты __getitem__, __contains__, get() — dict-подобный доступ."""

    def test_getitem_returns_value(self) -> None:
        """
        obj["key"] возвращает значение атрибута.

        ReadableMixin.__getitem__ делегирует в getattr(self, key).
        Работает единообразно для pydantic, dataclass и обычных классов.
        """
        # Arrange — объект с атрибутом name
        obj = SimpleReadable(name="Alice")

        # Act — чтение через квадратные скобки
        result = obj["name"]

        # Assert — значение извлечено из атрибута obj.name
        assert result == "Alice"

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        obj["missing"] бросает KeyError для несуществующего атрибута.

        ReadableMixin.__getitem__ ловит AttributeError от getattr
        и перебрасывает как KeyError — поведение идентично dict.
        """
        # Arrange — объект без атрибута "missing"
        obj = SimpleReadable(name="Alice")

        # Act & Assert — getattr бросает AttributeError,
        # __getitem__ оборачивает в KeyError
        with pytest.raises(KeyError):
            _ = obj["missing"]

    def test_contains_existing_key(self) -> None:
        """
        "key" in obj — True если атрибут существует.

        ReadableMixin.__contains__ делегирует в hasattr(self, key).
        """
        # Arrange — объект с атрибутом name
        obj = SimpleReadable(name="Alice")

        # Act & Assert — hasattr возвращает True для существующего атрибута
        assert "name" in obj

    def test_contains_missing_key(self) -> None:
        """
        "missing" in obj — False если атрибут не существует.
        """
        # Arrange — объект без атрибута "missing"
        obj = SimpleReadable(name="Alice")

        # Act & Assert — hasattr возвращает False
        assert "missing" not in obj

    def test_get_existing_key(self) -> None:
        """
        obj.get("key") возвращает значение существующего атрибута.

        ReadableMixin.get() делегирует в getattr(self, key, default).
        """
        # Arrange — объект с атрибутом value
        obj = SimpleReadable(value=42)

        # Act — безопасное чтение существующего ключа
        result = obj.get("value")

        # Assert — значение атрибута
        assert result == 42

    def test_get_missing_key_returns_default(self) -> None:
        """
        obj.get("missing", default) возвращает default.

        Если атрибут не существует, getattr возвращает default
        вместо бросания AttributeError.
        """
        # Arrange — объект без атрибута "missing"
        obj = SimpleReadable(value=42)

        # Act — чтение несуществующего ключа с явным default
        result = obj.get("missing", "fallback")

        # Assert — возвращён default
        assert result == "fallback"

    def test_get_missing_key_without_default_returns_none(self) -> None:
        """
        obj.get("missing") без default возвращает None.

        Default по умолчанию в ReadableMixin.get() — None.
        """
        # Arrange — объект без атрибута "missing"
        obj = SimpleReadable(value=42)

        # Act — чтение без explicit default
        result = obj.get("missing")

        # Assert — None как default по умолчанию
        assert result is None

    def test_getitem_on_pydantic_model(self) -> None:
        """
        __getitem__ работает на pydantic BaseModel через getattr.

        Pydantic хранит значения полей в атрибутах экземпляра.
        getattr(params, "name") возвращает значение поля,
        включая extra-поля для моделей с extra="allow".
        """
        # Arrange — pydantic-модель BaseResult с extra-полем
        result = BaseResult()
        result["metric"] = 99.5

        # Act — чтение extra-поля через __getitem__
        value = result["metric"]

        # Assert — getattr нашёл значение в __pydantic_extra__
        assert value == 99.5
