# ActionMachine/Auth/ContextAssembler.py
"""
Абстрактный сборщик метаданных запроса.

Конкретные реализации должны извлекать из объекта запроса (Request для FastAPI,
словаря для MCP и т.д.) все метаданные, которые впоследствии будут использованы
для формирования RequestInfo в контексте.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ContextAssembler(ABC):
    """
    Интерфейс сборщика метаданных.

    Метод assemble получает исходный объект запроса (протокол-специфичный)
    и возвращает словарь, который будет использован для создания RequestInfo.
    В словаре могут быть поля: trace_id, request_timestamp, client_ip и т.д.
    """

    @abstractmethod
    def assemble(self, request_data: Any) -> Dict[str, Any]:
        """
        Извлекает метаданные из запроса.

        :param request_data: объект запроса (например, fastapi.Request)
        :return: словарь с метаданными для последующего создания RequestInfo
        """
        pass