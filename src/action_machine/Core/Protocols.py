"""
Протоколы единого доступа к данным для ActionMachine.

Определяет минимальные интерфейсы, которым должны соответствовать все объекты,
используемые как параметры (Params) и результаты (Result) в действиях.
Позволяет единообразно работать как с dataclass (через миксины), так и с TypedDict.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadableDataProtocol(Protocol):
    """
    Протокол для чтения данных.

    Объект, реализующий этот протокол, должен предоставлять dict-подобный доступ
    для чтения полей. Используется для параметров (Params) и для state в плагинах.
    """

    def __getitem__(self, key: str) -> object:
        """Возвращает значение по ключу. Должен бросать KeyError, если ключ отсутствует."""
        ...

    def __contains__(self, key: str) -> bool:
        """Проверяет наличие ключа."""
        ...

    def get(self, key: str, default: object = None) -> object:
        """Безопасное получение значения с дефолтом."""
        ...

    def keys(self) -> Iterable[str]:
        """Возвращает итератор по ключам."""
        ...

    def values(self) -> Iterable[object]:
        """Возвращает итератор по значениям."""
        ...

    def items(self) -> Iterable[tuple[str, object]]:
        """Возвращает итератор по парам (ключ, значение)."""
        ...


@runtime_checkable
class WritableDataProtocol(ReadableDataProtocol, Protocol):
    """
    Протокол для чтения и записи данных.

    Добавляет возможность записи через __setitem__. Используется для результатов (Result),
    которые могут быть изменены плагинами (например, для дебага или модификации).
    """

    def __setitem__(self, key: str, value: object) -> None:
        """Устанавливает значение по ключу."""
        ...
