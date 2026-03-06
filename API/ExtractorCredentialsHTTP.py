# API/ExtractorCredentialsHTTP.py
"""
Конкретная реализация экстрактора учётных данных для HTTP-запросов (FastAPI).
Извлекает API-ключ из заданного HTTP-заголовка (по умолчанию X-API-Key).
Реализует интерфейс CredentialExtractor из ActionEngine.Auth.
"""

from typing import Dict, Any

from fastapi import Request
from ActionEngine.Auth.CredentialExtractor import CredentialExtractor


class ExtractorCredentialsHTTP(CredentialExtractor):
    """
    Извлекает учётные данные из HTTP-запроса FastAPI.

    Атрибуты:
        header_name: имя заголовка, в котором ожидается API-ключ (по умолчанию "X-API-Key").

    Метод extract возвращает словарь с ключом "api_key", если заголовок присутствует,
    иначе пустой словарь.
    """

    def __init__(self, header_name: str = "X-API-Key"):
        """
        Инициализирует экстрактор с указанным именем заголовка.

        :param header_name: имя HTTP-заголовка, содержащего API-ключ (регистр не важен).
        """
        self.header_name = header_name

    def extract(self, request_data: Request) -> Dict[str, Any]:
        """
        Извлекает API-ключ из заголовка запроса.

        :param request_data: объект fastapi.Request
        :return: словарь вида {"api_key": значение} или пустой словарь, если заголовок отсутствует.
        """
        # Извлекаем значение заголовка (без учёта регистра)
        api_key = request_data.headers.get(self.header_name)
        if api_key:
            return {"api_key": api_key}
        return {}