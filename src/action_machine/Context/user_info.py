"""
Компонент контекста, содержащий информацию о пользователе, инициировавшем действие.
Используется внутри класса Context для хранения данных об аутентифицированном пользователе.
Реализует ReadableDataProtocol через ReadableMixin для обеспечения dict-подобного доступа.
"""

from dataclasses import dataclass, field
from typing import Any

from action_machine.core.readable_mixin import ReadableMixin


@dataclass
class UserInfo(ReadableMixin):
    """
    Информация о пользователе.

    Этот датакласс является частью контекста выполнения и хранит идентификатор пользователя,
    его роли, а также дополнительные произвольные данные, которые могут быть добавлены
    при аутентификации (например, имя ключа, способ аутентификации и т.п.).

    Благодаря наследованию от ReadableMixin, объект UserInfo поддерживает dict-подобный доступ:
    - user["user_id"], user.get("roles"), "user_id" in user, user.keys(), user.values(), user.items().
    При этом сохраняется и атрибутный доступ (user.user_id).

    Атрибуты:
        user_id: Уникальный идентификатор пользователя (строка). Может быть None для гостя.
        roles: Список ролей пользователя (например, ["user", "admin"]). По умолчанию пустой список.
        extra: Словарь для хранения любых дополнительных данных, специфичных для конкретного
               способа аутентификации или бизнес-логики.

    Пример:
        >>> user = UserInfo(user_id="john_doe", roles=["user", "manager"])
        >>> print(user.user_id)
        john_doe
        >>> print(user["user_id"])
        john_doe
        >>> user.extra["auth_method"] = "api_key"
    """

    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
