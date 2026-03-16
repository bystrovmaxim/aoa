"""
Базовый класс для результата выполнения действия.

Реализует протокол WritableDataProtocol через WritableMixin.
Обеспечивает единый dict-доступ для чтения и записи.
"""

from .DataAccessMixins import WritableMixin


class BaseResult(WritableMixin):
    """
    Результат действия.

    Наследуйте этот класс для создания конкретных результатов.
    Может быть изменяемым (например, для плагинов).
    """
    pass