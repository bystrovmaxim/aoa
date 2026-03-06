# EntryPoint/Auth/EnvApiKeyAuthenticator.py
"""
Конкретная реализация аутентификатора для API-ключей, читаемых из переменных окружения.
"""

import os
from typing import Optional, Dict, Any
from ActionEngine.Auth import Authenticator
from ActionEngine import UserInfo


class EnvApiKeyAuthenticator(Authenticator):
    """
    Аутентификатор API-ключей на основе переменных окружения.

    Ожидает, что в окружении есть переменные с префиксом "API_KEY_", например:
        API_KEY_N8N=secret123:system:user,automation
        API_KEY_ADMIN=admin-secret:admin:admin

    Формат значения переменной:
        <секретный_ключ>:<user_id>:<роль1>,<роль2>...

    После загрузки ключей в память аутентификатор может быстро проверять поступивший ключ
    и возвращать соответствующий объект UserInfo.

    Атрибуты:
        keys: внутренний словарь, отображающий секретный ключ на объект UserInfo.
    """

    def __init__(self):
        """
        Инициализирует аутентификатор, загружая ключи из переменных окружения.
        """
        self.keys: Dict[str, UserInfo] = self._load_keys()

    def _load_keys(self) -> Dict[str, UserInfo]:
        """
        Загружает ключи из переменных окружения.

        Проходит по всем переменным, начинающимся с "API_KEY_", парсит их значение
        и заполняет внутренний словарь.

        :return: словарь {секретный_ключ: UserInfo}
        """
        keys = {}
        for env_name, env_value in os.environ.items():
            if env_name.startswith("API_KEY_"):
                # Ожидаемый формат: ключ:user_id:роль1,роль2
                parts = env_value.split(':', 2)
                if len(parts) >= 2:
                    secret_key = parts[0]
                    user_id = parts[1]
                    roles = parts[2].split(',') if len(parts) > 2 else []
                    keys[secret_key] = UserInfo(
                        user_id=user_id,
                        roles=roles,
                        extra={"key_name": env_name[8:]}  # сохраняем имя ключа без префикса
                    )
        return keys

    def authenticate(self, credentials: Dict[str, Any]) -> Optional[UserInfo]:
        """
        Проверяет, существует ли переданный ключ во внутреннем словаре.

        :param credentials: словарь, содержащий ключ "api_key" (из экстрактора)
        :return: объект UserInfo, если ключ найден, иначе None
        """
        api_key = credentials.get("api_key")
        if not api_key:
            return None
        return self.keys.get(api_key)