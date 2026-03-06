# ActionEngine/Auth/AuthCoordinator.py
"""
Координатор аутентификации.

Объединяет три стратегии:
- CredentialExtractor – извлечение учётных данных из запроса.
- Authenticator – проверка учётных данных и получение UserInfo.
- ContextAssembler – сбор метаданных запроса.

Координатор управляет последовательностью вызовов и создаёт итоговый Context,
используя UserInfo от аутентификатора и метаданные от ассемблера.
"""

from typing import Optional, Any

from .CredentialExtractor import CredentialExtractor
from .Authenticator import Authenticator
from .ContextAssembler import ContextAssembler
from ..Context import Context, RequestInfo


class AuthCoordinator:
    """
    Координатор аутентификации.

    Атрибуты:
        extractor: стратегия извлечения учётных данных.
        authenticator: стратегия проверки учётных данных.
        assembler: стратегия сбора метаданных запроса.
    """

    def __init__(
        self,
        extractor: CredentialExtractor,
        authenticator: Authenticator,
        assembler: ContextAssembler,
    ):
        """
        Инициализирует координатор с заданными стратегиями.

        :param extractor: объект, реализующий CredentialExtractor.
        :param authenticator: объект, реализующий Authenticator.
        :param assembler: объект, реализующий ContextAssembler.
        """
        self.extractor = extractor
        self.authenticator = authenticator
        self.assembler = assembler

    def process(self, request_data: Any) -> Optional[Context]:
        """
        Выполняет полный цикл аутентификации и создания контекста.

        :param request_data: объект запроса (зависит от протокола).
        :return: Context в случае успеха, None при неудаче.
        """
        # 1. Извлечение учётных данных
        credentials = self.extractor.extract(request_data)
        if not credentials:
            return None

        # 2. Аутентификация
        user_info = self.authenticator.authenticate(credentials)
        if not user_info:
            return None

        # 3. Сбор метаданных запроса
        metadata = self.assembler.assemble(request_data)

        # 4. Создание RequestInfo из метаданных
        req_info = RequestInfo(**metadata)

        # 5. Создание итогового контекста
        # (окружение можно добавить позже, например, передав в конструктор Context)
        return Context(user=user_info, request=req_info, environment=None)