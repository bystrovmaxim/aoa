# Файл: ActionEngine/CheckRoles.py
"""
Декоратор для указания требуемых ролей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from typing import List, Union

class CheckRoles:
    """
    Декоратор для задания требований к ролям пользователя.

    Константы:
        NONE — доступ без роли (гость).
        ANY — требуется любая роль (аутентифицированный пользователь).

    Можно также передать список конкретных ролей, например:
        @CheckRoles(["admin", "manager"])
    """
    NONE = "NO_ROLE"
    ANY = "ANY_ROLE"

    def __init__(self, 
                 spec: Union[str, List[str]],
                 description: str = None):
        """
        Параметры:
            spec: строка (одна роль), список строк, или константа NONE/ANY.
        """
        self.spec = spec
        self.description = description

    def __call__(self, cls):
        """
        Добавляет спецификацию ролей в класс как атрибут _role_spec.
        """
        cls._role_spec = self.spec
        return cls