# ActionMachine/Context/UserInfo.py
"""
Компонент контекста, содержащий информацию о пользователе, инициировавшем действие.
Используется внутри класса Context для хранения данных об аутентифицированном пользователе.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class UserInfo:
    """
    Информация о пользователе.

    Этот датакласс является частью контекста выполнения и хранит идентификатор пользователя,
    его роли, а также дополнительные произвольные данные, которые могут быть добавлены
    при аутентификации (например, имя ключа, способ аутентификации и т.п.).

    Атрибуты:
        user_id: Уникальный идентификатор пользователя (строка). Может быть None для гостя.
        roles: Список ролей пользователя (например, ["user", "admin"]). По умолчанию пустой список.
        extra: Словарь для хранения любых дополнительных данных, специфичных для конкретного
               способа аутентификации или бизнес-логики.

    Пример:
        >>> user = UserInfo(user_id="john_doe", roles=["user", "manager"])
        >>> print(user.user_id)
        john_doe
        >>> user.extra["auth_method"] = "api_key"
    """
    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)