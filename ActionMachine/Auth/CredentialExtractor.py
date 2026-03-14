from abc import ABC, abstractmethod
from typing import Any, Dict


class CredentialExtractor(ABC):
    """
    Базовый класс для извлечения учётных данных из запроса.
    """

    @abstractmethod
    def extract(self, request_data: Any) -> Dict[str, Any]:
        """
        Извлекает учётные данные из объекта запроса.

        :param request_data: объект запроса (например, fastapi.Request)
        :return: словарь с учётными данными или пустой словарь
        """
        pass
