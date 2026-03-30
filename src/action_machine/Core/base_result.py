# ActionMachine/Core/BaseResult.py
"""
Базовый класс для результата выполнения действия.

Наследует ReadableMixin и WritableMixin, обеспечивая dict-подобный интерфейс
для чтения и записи полей результата.

Реализует протокол WritableDataProtocol через комбинацию миксинов.
Не содержит собственных методов — вся функциональность
наследуется из ReadableMixin (get, keys, items, resolve)
и WritableMixin (__setitem__, __delitem__, write, update).

Наследуйте BaseResult для создания конкретных результатов действий.
Поля результата определяются как атрибуты класса или задаются
динамически через dict-подобный доступ.

Поддерживает:
    - dict-подобный доступ: result['key'], result['key'] = value
    - атрибутный доступ:    result.key,    result.key = value
    - итерацию по парам:    result.items()
    - dot-path разрешение:  result.resolve('nested.key')
    - контролируемую запись: result.write('key', value, allowed_keys=[...])

Пример:
    >>> result = BaseResult()
    >>> result['status'] = 'ok'
    >>> result.message = 'Done'
    >>> result['message']
    'Done'
    >>> result.items()
    [('status', 'ok'), ('message', 'Done')]
"""

from .readable_mixin import ReadableMixin
from .writable_mixin import WritableMixin


class BaseResult(ReadableMixin, WritableMixin):
    """
    Результат действия.

    Наследуйте этот класс для создания конкретных результатов.
    Может быть изменяемым — плагины и аспекты могут дополнять
    результат новыми полями через dict-подобный интерфейс.

    Пример наследования:
        class OrderResult(BaseResult):
            order_id: str
            total: float
            status: str = "created"
    """

    pass
