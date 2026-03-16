
class WritableMixin():
    """
    Добавляет возможность записи через __setitem__.
    Используется для результатов (Result).
    """

    def __setitem__(self, key: str, value: object) -> None:
        setattr(self, key, value)