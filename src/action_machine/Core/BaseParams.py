"""
Базовый класс для входных параметров действия.

Реализует протокол ReadableDataProtocol через ReadableMixin.
Обеспечивает единый dict-доступ к полям.
"""

from .ReadableMixin import ReadableMixin


class BaseParams(ReadableMixin):
    """
    Параметры действия.

    Наследуйте этот класс для создания конкретных параметров.
    Рекомендуется использовать @dataclass(frozen=True) для иммутабельности.
    """

    pass
