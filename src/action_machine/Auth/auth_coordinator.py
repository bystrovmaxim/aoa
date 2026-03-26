# src/action_machine/Auth/auth_coordinator.py
"""
Координатор процесса аутентификации и сборки контекста.

Объединяет извлечение учётных данных, аутентификацию и сбор метаданных.
Все методы асинхронные, так как делегируют работу асинхронным компонентам.
"""

from typing import Any

# Строгие и явные импорты вместо фасадов
from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo

from .authenticator import Authenticator
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor


class AuthCoordinator:
    """
    Координатор, управляющий процессом создания контекста выполнения.

    Последовательно вызывает:
    1. Извлечение учётных данных из запроса.
    2. Аутентификация (проверку учётных данных).
    3. Сбор метаданных запроса.
    """

    def __init__(
        self,
        extractor: CredentialExtractor,
        auth_instance: Authenticator,
        assembler: ContextAssembler,
    ) -> None:
        self.extractor = extractor
        self.authenticator = auth_instance
        self.assembler = assembler

    async def process(self, request_data: Any) -> Context | None:
        """
        Асинхронно выполняет полный цикл аутентификации и сборки контекста.
        """
        # Шаг 1: извлечение учётных данных
        credentials = await self.extractor.extract(request_data)
        if not credentials:
            return None

        # Шаг 2: аутентификация
        authenticated_user = await self.authenticator.authenticate(credentials)
        if not authenticated_user:
            return None

        # Шаг 3: сбор метаданных
        metadata = await self.assembler.assemble(request_data)
        req_info = RequestInfo(**metadata)

        # Шаг 4: формирование контекста
        return Context(
            user=authenticated_user,
            request=req_info,
            runtime=None  # будет заполнен позже или останется пустым
        )
