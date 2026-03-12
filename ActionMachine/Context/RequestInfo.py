# ActionMachine/Context/RequestInfo.py
"""
Компонент контекста, содержащий метаданные входящего запроса.
Используется для хранения информации, специфичной для протокола вызова (HTTP, MCP и т.д.).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class RequestInfo:
    """
    Метаданные входящего запроса.

    Содержит всю информацию, которая может быть полезна для логирования, трассировки,
    анализа производительности и аудита. Заполняется на входе в систему (в FastAPI-зависимости
    или MCP-обработчике) и затем передаётся в контексте.

    Атрибуты:
        trace_id: Уникальный идентификатор запроса для сквозной трассировки (например, для OpenTelemetry).
        request_timestamp: Время получения запроса (в UTC).
        request_path: Путь эндпоинта (для HTTP) или имя инструмента (для MCP).
        request_method: HTTP-метод (GET, POST, ...) или "tool_call" для MCP.
        full_url: Полный URL запроса (только для HTTP).
        client_ip: IP-адрес клиента (если доступен).
        protocol: Протокол вызова ("http", "https", "mcp").
        user_agent: Заголовок User-Agent (для HTTP).
        extra: Дополнительные поля, специфичные для конкретного протокола или приложения.
        tags: Произвольные теги для маркировки запроса (например, для A/B-тестирования).

    Пример:
        >>> req = RequestInfo(
        ...     trace_id="abc-123",
        ...     request_timestamp=datetime.utcnow(),
        ...     request_path="/api/v1/init_database",
        ...     request_method="POST",
        ...     client_ip="192.168.1.1"
        ... )
        >>> req.tags["ab_test"] = "control"
    """
    trace_id: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    full_url: Optional[str] = None
    client_ip: Optional[str] = None
    protocol: Optional[str] = None
    user_agent: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)