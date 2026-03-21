# src/action_machine/Auth/auth_coordinator.py
"""
Координатор процесса аутентификации и сборки контекста.

Объединяет извлечение учётных данных, аутентификацию и сбор метаданных.
Все методы асинхронные, так как делегируют работу асинхронным компонентам.
"""

from typing import Any

from ..Context import Context, RequestInfo
from .authenticator import Authenticator
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor


class AuthCoordinator:
    """
    Координатор, управляющий процессом создания контекста выполнения.

    Последовательно вызывает:
    1. Извлечение учётных данных из запроса.
    2. Аутентификацию (проверку учётных данных).
    3. Сбор метаданных запроса.

    Результат — полностью сформированный Context, содержащий информацию
    о пользователе, запросе и окружении.

    Атрибуты:
        extractor: Извлекатель учётных данных.
        authenticator: Аутентификатор.
        assembler: Сборщик метаданных.
    """

    def __init__(
        self,
        extractor: CredentialExtractor,
        auth_instance: Authenticator,  # Переименовано для избежания конфликта имён
        assembler: ContextAssembler,
    ) -> None:
        """
        Инициализирует координатор аутентификации.

        Аргументы:
            extractor: Извлекатель учётных данных из запроса.
                       Должен реализовывать интерфейс credential_extractor.
            auth_instance: Аутентификатор для проверки учётных данных.
                           Должен реализовывать интерфейс authenticator.
            assembler: Сборщик метаданных запроса.
                       Должен реализовывать интерфейс context_assembler.

        Пример:
            >>> coordinator = auth_coordinator(
            ...     extractor=HeaderTokenExtractor(),
            ...     auth_instance=JWTAuthenticator(secret_key="my-secret"),
            ...     assembler=FastAPIRequestAssembler()
            ... )

        Примечание:
            Параметр назван auth_instance, а не authenticator, чтобы избежать
            предупреждения Pylint W0621 (redefined-outer-name), так как имя
            'authenticator' уже используется как имя класса и модуля.
        """
        self.extractor = extractor
        self.authenticator = auth_instance
        self.assembler = assembler

    async def process(self, request_data: Any) -> Context | None:
        """
        Асинхронно выполняет полный цикл аутентификации и сборки контекста.

        Алгоритм работы:
        1. Извлечение учётных данных из request_data через extractor.
        2. Если учётные данные отсутствуют → возврат None.
        3. Аутентификация учётных данных через authenticator.
        4. Если аутентификация не удалась → возврат None.
        5. Сбор метаданных запроса через assembler.
        6. Формирование и возврат полного контекста.

        Аргументы:
            request_data: Исходные данные запроса.
                          Может быть любым объектом (dict, Request, и т.д.),
                          который понимают экстрактор и сборщик.

        Возвращает:
            Context с информацией о пользователе, запросе и окружении,
            или None, если аутентификация не удалась.

        Исключения:
            Могут пробрасываться исключения от компонентов:
            - extractor.extract()
            - authenticator.authenticate()
            - assembler.assemble()

        Пример:
            >>> result = await coordinator.process({
            ...     "headers": {"Authorization": "Bearer token"},
            ...     "method": "POST",
            ...     "path": "/api/data"
            ... })
            >>> if result:
            ...     print(f"User: {result.user.user_id}")
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