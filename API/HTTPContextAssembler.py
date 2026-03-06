# API/HTTPContextAssembler.py
"""
Конкретная реализация сборщика метаданных для HTTP-запросов (FastAPI).
Извлекает из объекта Request информацию, полезную для логирования,
трассировки и телеметрии.
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import Request
from ActionEngine.Auth.ContextAssembler import ContextAssembler


class HTTPContextAssembler(ContextAssembler):
    """
    Сборщик метаданных для HTTP-запросов.

    Извлекает:
      - trace_id (из заголовка X-Trace-ID или генерирует новый)
      - request_timestamp (время получения запроса в UTC)
      - request_path (путь эндпоинта)
      - request_method (HTTP-метод)
      - full_url (полный URL)
      - client_ip (IP клиента)
      - protocol (http/https)
      - user_agent (заголовок User-Agent)
      - tags (из заголовка X-Tags, формат ключ1=значение1,ключ2=значение2)
    """

    def assemble(self, request_data: Request) -> Dict[str, Any]:
        """
        Извлекает метаданные из FastAPI-запроса.

        :param request_data: объект fastapi.Request
        :return: словарь с метаданными
        """
        metadata: Dict[str, Any] = {
            "trace_id": request_data.headers.get("x-trace-id", str(uuid.uuid4())),
            "request_timestamp": datetime.utcnow(),
            "request_path": request_data.url.path,
            "request_method": request_data.method,
            "full_url": str(request_data.url),
            "client_ip": request_data.client.host if request_data.client else None,
            "protocol": request_data.url.scheme,
            "user_agent": request_data.headers.get("user-agent"),
        }

        # Обработка тегов
        tags_header = request_data.headers.get("x-tags")
        if tags_header:
            tags = {}
            for pair in tags_header.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    tags[k.strip()] = v.strip()
            metadata["tags"] = tags

        return metadata