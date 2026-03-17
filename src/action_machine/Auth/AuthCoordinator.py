"""
Координатор процесса аутентификации и сборки контекста.

Объединяет извлечение учётных данных, аутентификацию и сбор метаданных.
Все методы асинхронные, так как делегируют работу асинхронным компонентам.
"""

from typing import Any

from ..Context import Context, request_info
from .Authenticator import authenticator
from .ContextAssembler import context_assembler
from .CredentialExtractor import credential_extractor


class auth_coordinator:
    """
    Координатор, управляющий процессом создания контекста выполнения.

    Последовательно вызывает:
    1. Извлечение учётных данных из запроса.
    2. Аутентификацию (проверку учётных данных).
    3. Сбор метаданных запроса.
    Результат — полностью сформированный Context.
    """

    def __init__(
        self,
        extractor: credential_extractor,
        authenticator: authenticator,
        assembler: context_assembler,
    ) -> None:
        """
        Инициализирует координатор.

        Аргументы:
            extractor: извлекатель учётных данных.
            authenticator: аутентификатор.
            assembler: сборщик метаданных.
        """
        self.extractor = extractor
        self.authenticator = authenticator
        self.assembler = assembler

    async def process(self, request_data: Any) -> Context | None:
        """
        Асинхронно выполняет полный цикл аутентификации и сборки контекста.

        Аргументы:
            request_data: исходные данные запроса.

        Возвращает:
            Context с информацией о пользователе, запросе и окружении,
            или None, если аутентификация не удалась.
        """
        credentials = await self.extractor.extract(request_data)
        if not credentials:
            return None
        user_info = await self.authenticator.authenticate(credentials)
        if not user_info:
            return None
        metadata = await self.assembler.assemble(request_data)
        req_info = request_info(**metadata)
        return Context(user=user_info, request=req_info, environment=None)
