from abc import ABC, abstractmethod
from typing import Any, Dict

class CredentialExtractor(ABC):
    @abstractmethod
    def extract(self, request_data: Any) -> Dict[str, Any]:
        """Возвращает словарь с учётными данными или пустой словарь."""
        pass