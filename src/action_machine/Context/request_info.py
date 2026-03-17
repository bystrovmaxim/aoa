"""
Компонент контекста, содержащий метаданные входящего запроса.
Используется для хранения информации, специфичной для протокола вызова (HTTP, MCP и т.д.).
Реализует ReadableDataProtocol через ReadableMixin для обеспечения dict-подобного доступа.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from action_machine.Core.ReadableMixin import ReadableMixin


@dataclass
class request_info(ReadableMixin):
    """
    Метаданные входящего запроса.

    Содержит всю информацию, которая может быть полезна для логирования, трассировки,
    анализа производительности и аудита. Заполняется на входе в систему (в FastAPI-зависимости
    или MCP-обработчике) и затем передаётся в контексте.

    Благодаря наследованию от ReadableMixin, объект RequestInfo поддерживает dict-подобный доступ:
    - request["trace_id"], request.get("request_path"), "client_ip" in request, request.keys() и т.д.

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
        >>> req["trace_id"]
        'abc-123'
        >>> req.tags["ab_test"] = "control"
    """

    trace_id: str | None = None
    request_timestamp: datetime | None = None
    request_path: str | None = None
    request_method: str | None = None
    full_url: str | None = None
    client_ip: str | None = None
    protocol: str | None = None
    user_agent: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
