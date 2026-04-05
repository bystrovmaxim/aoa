# src/action_machine/core/base_state.py
"""
BaseState — frozen-состояние конвейера аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseState — неизменяемый объект, хранящий накопленные данные между шагами
конвейера аспектов. Каждый regular-аспект возвращает dict с новыми полями,
машина (ActionProductMachine) проверяет их чекерами и создаёт НОВЫЙ
BaseState, объединяя предыдущие данные с новыми. Аспект получает state
только на чтение — мутация невозможна после создания.

═══════════════════════════════════════════════════════════════════════════════
FROZEN-СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

BaseState полностью неизменяем после создания:

- ``__setattr__`` выбрасывает ``AttributeError`` (кроме инициализации
  через ``object.__setattr__`` в ``__init__``).
- ``__delattr__`` выбрасывает ``AttributeError``.
- Нет методов ``__setitem__``, ``__delitem__``, ``write``, ``update``.

Единственный способ «изменить» состояние — создать новый экземпляр:

    old_state = BaseState({"total": 100})
    new_state = BaseState({**old_state.to_dict(), "discount": 10})

Это гарантирует, что аспект не может записать данные в state напрямую,
обойдя чекеры. Машина контролирует каждое добавление поля через валидацию
dict, возвращённого аспектом.

═══════════════════════════════════════════════════════════════════════════════
НАСЛЕДОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseState наследует ``ReadableMixin``, что обеспечивает:

- Dict-подобный доступ на чтение: ``state["key"]``, ``state.get("key")``.
- Навигацию по вложенным объектам: ``state.resolve("nested.field")``.
- Итерацию: ``state.keys()``, ``state.values()``, ``state.items()``.
- Проверку наличия: ``"key" in state``.

═══════════════════════════════════════════════════════════════════════════════
КОНВЕЙЕР АСПЕКТОВ — КАК STATE ИСПОЛЬЗУЕТСЯ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    1. Машина создаёт пустой state: ``state = BaseState()``.
    2. Для каждого regular-аспекта:
       a. Вызывает аспект, передавая текущий frozen state.
       b. Аспект возвращает dict с новыми полями.
       c. Машина проверяет dict чекерами.
       d. Машина создаёт новый state: ``BaseState({**state.to_dict(), **new_dict})``.
    3. Summary-аспект получает финальный frozen state и формирует Result.

На каждом шаге state — новый объект. Предыдущий state не модифицируется.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ BaseParams И BaseResult
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  — pydantic BaseModel, frozen=True. Входные параметры действия.
    BaseResult  — pydantic BaseModel, frozen=True. Результат действия.
    BaseState   — обычный класс (не pydantic), frozen. Промежуточное состояние
                  конвейера. Не pydantic, потому что поля динамические —
                  определяются возвращаемыми dict аспектов, а не схемой класса.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Создание с начальными данными
    state = BaseState({"total": 1500, "user": "agent"})

    # Чтение
    state["total"]            # → 1500
    state.get("user")         # → "agent"
    state.resolve("user")     # → "agent"
    state.to_dict()           # → {"total": 1500, "user": "agent"}

    # Запись запрещена
    state["count"] = 42       # → AttributeError
    state.processed = True    # → AttributeError
    del state["total"]        # → AttributeError

    # «Изменение» — создание нового экземпляра
    new_state = BaseState({**state.to_dict(), "count": 42})
    new_state["count"]        # → 42
    new_state["total"]        # → 1500 (унаследовано)
"""

from typing import Any

from .readable_mixin import ReadableMixin


class BaseState(ReadableMixin):
    """
    Frozen-состояние конвейера аспектов.

    Инициализируется из словаря. Все ключи становятся атрибутами.
    После создания запись и удаление атрибутов запрещены.

    Поддерживает dict-подобный доступ на чтение через ReadableMixin:
    ``state["key"]``, ``state.get("key")``, ``state.keys()``,
    ``state.resolve("nested.path")``.
    """

    # Флаг, разрешающий запись только во время __init__.
    # Создаётся через type.__setattr__ на уровне класса,
    # поэтому не попадает под проверку экземплярного __setattr__.
    _initializing: bool = False

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        """
        Инициализирует frozen-состояние.

        Каждая пара (ключ, значение) из словаря записывается как атрибут
        через ``object.__setattr__``, минуя переопределённый ``__setattr__``.
        После завершения ``__init__`` любая запись запрещена.

        Аргументы:
            initial: начальные значения. Ключи становятся атрибутами.
                     None или пустой словарь — пустое состояние.

        Пример:
            >>> state = BaseState({"total": 1500})
            >>> state.total
            1500
            >>> state = BaseState()
            >>> state.to_dict()
            {}
        """
        if initial:
            for key, value in initial.items():
                object.__setattr__(self, key, value)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Запрещает запись атрибутов. BaseState полностью frozen после создания.

        Исключения:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"BaseState является frozen-объектом. "
            f"Запись атрибута '{name}' запрещена. "
            f"Создайте новый BaseState с нужными данными: "
            f"BaseState({{**state.to_dict(), '{name}': value}})."
        )

    def __delattr__(self, name: str) -> None:
        """
        Запрещает удаление атрибутов. BaseState полностью frozen после создания.

        Исключения:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"BaseState является frozen-объектом. "
            f"Удаление атрибута '{name}' запрещено."
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Возвращает словарь всех публичных атрибутов состояния.

        Используется машиной для создания нового BaseState при мерже
        с результатом аспекта, а также для передачи в плагины
        (PluginEvent.state_aspect) и логгеры.

        Фильтрует приватные атрибуты (начинающиеся с '_').

        Возвращает:
            dict[str, Any] — словарь {ключ: значение} публичных полей.

        Пример:
            >>> state = BaseState({"a": 1, "b": 2})
            >>> state.to_dict()
            {'a': 1, 'b': 2}
        """
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

    def __repr__(self) -> str:
        """
        Человекочитаемое представление для отладки.

        Формат: ``BaseState(key1=value1, key2=value2, ...)``.

        Возвращает:
            str — строковое представление объекта.

        Пример:
            >>> state = BaseState({"total": 1500})
            >>> repr(state)
            "BaseState(total=1500)"
        """
        fields: dict[str, Any] = self.to_dict()
        pairs: str = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{type(self).__name__}({pairs})"
