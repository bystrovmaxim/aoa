# ActionMachine/Core/BaseParams.py
"""
Базовый класс для параметров действия.

Наследует только ReadableMixin — параметры действия являются
неизменяемыми (read-only) после создания. WritableMixin не используется,
чтобы предотвратить случайное изменение входных данных
аспектами или плагинами в ходе выполнения конвейера.

Это принципиальное отличие от BaseState и BaseResult,
которые наследуют оба миксина (ReadableMixin + WritableMixin):
    - BaseParams  — только чтение (входные данные действия).
    - BaseState   — чтение и запись (состояние конвейера аспектов).
    - BaseResult  — чтение и запись (результат действия).

Поддерживает:
    - dict-подобный доступ на чтение: params['key'], params.get('key')
    - атрибутный доступ:              params.key
    - итерацию по парам:              params.items(), params.keys()
    - dot-path разрешение:            params.resolve('nested.key')
    - проверку наличия:               'key' in params

Не поддерживает (намеренно):
    - params['key'] = value   → AttributeError
    - del params['key']       → AttributeError
    - params.write(...)       → AttributeError

Наследуйте BaseParams для создания конкретных параметров действий.
Поля параметров определяются как атрибуты класса (рекомендуется dataclass).

Пример:
    >>> from dataclasses import dataclass
    >>> @dataclass
    ... class OrderParams(BaseParams):
    ...     order_id: str
    ...     amount: float
    ...     currency: str = "RUB"
    >>> params = OrderParams(order_id="ORD-123", amount=1500.0)
    >>> params['order_id']
    'ORD-123'
    >>> params.resolve('currency')
    'RUB'
    >>> params.items()
    [('order_id', 'ORD-123'), ('amount', 1500.0), ('currency', 'RUB')]
"""

from .ReadableMixin import ReadableMixin


class BaseParams(ReadableMixin):
    """
    Параметры действия (read-only).

    Наследуйте этот класс для создания конкретных параметров.
    Рекомендуется использовать @dataclass для определения полей.

    Параметры передаются в конвейер аспектов и доступны на всех этапах:
    validate, prepare, handle, summary. Аспекты читают параметры,
    но не могут их изменять — для изменяемых данных используется
    BaseState (state).

    Пример наследования:
        @dataclass
        class CreateUserParams(BaseParams):
            username: str
            email: str
            role: str = "user"
    """

    pass