from abc import ABC, abstractmethod
from typing import Optional, Any
from ..Context.UserInfo import UserInfo


class Authenticator(ABC):
    """
    Базовый класс для всех аутентификаторов.
    Преобразует предоставленные учётные данные в информацию о пользователе.
    """

    @abstractmethod
    def authenticate(self, credentials: Any) -> Optional[UserInfo]:
        """
        Принимает учётные данные (строку API-ключа, логин/пароль, JWT и т.д.)
        Возвращает UserInfo в случае успеха, иначе None.
        """
        pass
