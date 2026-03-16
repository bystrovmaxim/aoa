"""
Миксины для реализации протоколов ReadableDataProtocol и WritableDataProtocol
на основе атрибутов объекта. Предназначены для использования в dataclass-классах,
наследующих BaseParams и BaseResult.
"""


class ReadableMixin:
    """
    Реализует ReadableDataProtocol через атрибуты объекта.

    Позволяет обращаться к полям dataclass как через точку, так и через dict-доступ.
    """

    def __getitem__(self, key: str) -> object:
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Возвращает список имён всех публичных полей (не начинающихся с '_')."""
        return [k for k in vars(self) if not k.startswith('_')]

    def values(self) -> list[object]:
        return [self[k] for k in self.keys()]

    def items(self) -> list[tuple[str, object]]:
        return [(k, self[k]) for k in self.keys()]


class WritableMixin(ReadableMixin):
    """
    Добавляет возможность записи через __setitem__.
    Используется для результатов (Result).
    """

    def __setitem__(self, key: str, value: object) -> None:
        setattr(self, key, value)