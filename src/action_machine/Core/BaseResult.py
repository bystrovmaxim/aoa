"""
Базовый класс для результата выполнения действия.

Реализует протокол WritableDataProtocol через комбинацию ReadableMixin и WritableMixin.
Обеспечивает единый dict-доступ для чтения и записи.
"""

from .ReadableMixin import ReadableMixin
from .WritableMixin import WritableMixin


class BaseResult(ReadableMixin, WritableMixin):
    """
    Результат действия.

    Наследуйте этот класс для создания конкретных результатов.
    Может быть изменяемым (например, для плагинов).
    """

    pass
