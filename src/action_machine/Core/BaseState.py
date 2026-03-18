# ActionMachine/Core/BaseState.py
"""
Базовый класс для состояния конвейера аспектов.

Наследует ReadableMixin и WritableMixin, обеспечивая dict-подобный интерфейс
для чтения и записи, а также поддержку dot-path разрешения через метод resolve.

Заменяет ранее использовавшийся неявный dict[str, Any] во всех аспектах
и плагинах. Все методы аспектов (validate, prepare, handle, summary и т.д.)
теперь принимают state: BaseState вместо state: dict[str, Any].

Преимущества замены dict → BaseState:
    1. Единообразный интерфейс — state поддерживает resolve, get, keys, items,
       write, update — как и все остальные объекты на основе ReadableMixin.
    2. Контролируемая запись — метод write(key, value, allowed_keys)
       позволяет ограничивать набор полей, доступных для изменения.
    3. Типизация — IDE и mypy видят конкретный тип BaseState,
       а не размытый dict[str, Any].
    4. Расширяемость — можно наследовать BaseState для добавления
       валидации, логирования изменений или иммутабельных полей.

Может быть инициализирован из словаря. Все ключи становятся атрибутами объекта.
Поддерживает dict-подобный доступ (obj['key']) и атрибутный доступ (obj.key).

Пример:
    >>> state = BaseState({"total": 1500, "user": "agent"})
    >>> state["count"] = 42
    >>> state.processed = True
    >>> state.resolve("user")
    'agent'
    >>> state.to_dict()
    {'total': 1500, 'user': 'agent', 'count': 42, 'processed': True}
"""

from typing import Any

from .ReadableMixin import ReadableMixin
from .WritableMixin import WritableMixin


class BaseState(ReadableMixin, WritableMixin):
    """
    Состояние конвейера аспектов.

    Может быть инициализировано из словаря. Все ключи становятся атрибутами.
    Поддерживает dict-подобный доступ (obj['key']) и атрибутный доступ (obj.key).
    Также предоставляет метод resolve для доступа по точечной нотации
    и метод write для контролируемой записи с валидацией.
    """

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        """
        Инициализирует состояние.

        Если передан словарь initial — каждая пара (key, value)
        устанавливается как атрибут объекта через setattr.
        None или пустой словарь означают пустое состояние.

        Аргументы:
            initial: начальные значения в виде словаря.
                     Ключи становятся атрибутами объекта.
                     None означает пустое состояние.

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
                setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """
        Возвращает словарь всех публичных атрибутов состояния.

        Используется для передачи состояния в логгеры, сериализаторы
        и другие компоненты, которые ожидают словарь.

        Делегирует вызов методу items() из ReadableMixin,
        который фильтрует атрибуты с префиксом '_'.

        Возвращает:
            dict[str, Any]: словарь с парами (ключ, значение)
            для всех публичных полей.

        Пример:
            >>> state = BaseState({"a": 1, "b": 2})
            >>> state.to_dict()
            {'a': 1, 'b': 2}
        """
        return dict(self.items())

    def __repr__(self) -> str:
        """
        Человекочитаемое представление состояния для отладки.

        Формат: BaseState(key1=value1, key2=value2, ...).

        Возвращает:
            str: строковое представление объекта.

        Пример:
            >>> state = BaseState({"total": 1500})
            >>> repr(state)
            "BaseState(total=1500)"
        """
        fields: dict[str, Any] = self.to_dict()
        pairs: str = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{type(self).__name__}({pairs})"