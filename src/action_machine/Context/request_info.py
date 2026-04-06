# src/action_machine/context/request_info.py
"""
RequestInfo — метаданные входящего запроса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

RequestInfo — компонент контекста выполнения (Context), содержащий
информацию о входящем запросе: трассировку, путь, метод, IP клиента,
протокол и другие метаданные, специфичные для протокола вызова
(HTTP, MCP и т.д.).

Заполняется на входе в систему (в ContextAssembler) и передаётся
в контексте для логирования, трассировки, анализа производительности
и аудита.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── RequestInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
FROZEN И FORBID
═══════════════════════════════════════════════════════════════════════════════

RequestInfo неизменяем после создания. Метаданные запроса фиксируются
один раз при входе и не меняются в ходе выполнения конвейера.

Произвольные поля запрещены (extra="forbid"). Если конкретному проекту
нужны дополнительные метаданные запроса (correlation_id, ab_variant,
feature_flags), создаётся наследник с явно объявленными полями:

    class ExtendedRequestInfo(RequestInfo):
        correlation_id: str | None = None
        ab_variant: str | None = None

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП В АСПЕКТАХ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к RequestInfo из аспекта невозможен. Единственный путь —
через @context_requires и ContextView:

    @regular_aspect("Логирование запроса")
    @context_requires(Ctx.Request.trace_id, Ctx.Request.client_ip)
    async def log_request_aspect(self, params, state, box, connections, ctx):
        trace = ctx.get(Ctx.Request.trace_id)     # → "abc-123"
        ip = ctx.get(Ctx.Request.client_ip)        # → "192.168.1.1"
        return {}

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    req = RequestInfo(trace_id="abc-123", client_ip="192.168.1.1")

    req["trace_id"]         # → "abc-123"
    "client_ip" in req      # → True
    list(req.keys())        # → ["trace_id", "request_timestamp", ...]

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from datetime import datetime

    req = RequestInfo(
        trace_id="abc-123",
        request_timestamp=datetime.utcnow(),
        request_path="/api/v1/orders",
        request_method="POST",
        client_ip="192.168.1.1",
        protocol="https",
    )

    req["trace_id"]                  # → "abc-123"
    req.resolve("request_method")    # → "POST"
    req.model_dump()                 # → {"trace_id": "abc-123", ...}

    # Расширение через наследование:
    class TracedRequestInfo(RequestInfo):
        correlation_id: str | None = None
        ab_variant: str | None = None

    req = TracedRequestInfo(
        trace_id="abc-123",
        correlation_id="corr-456",
        ab_variant="control",
    )
"""

from datetime import datetime

from pydantic import ConfigDict

from action_machine.core.base_schema import BaseSchema


class RequestInfo(BaseSchema):
    """
    Метаданные входящего запроса.

    Frozen после создания. Произвольные поля запрещены.
    Расширение — только через наследование с явными полями.

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.

    Атрибуты:
        trace_id: уникальный ID запроса для сквозной трассировки
                  (например, для OpenTelemetry).
        request_timestamp: время получения запроса (в UTC).
        request_path: путь эндпоинта (для HTTP) или имя инструмента (для MCP).
        request_method: HTTP-метод (GET, POST, ...) или "tool_call" для MCP.
        full_url: полный URL запроса (только для HTTP).
        client_ip: IP-адрес клиента (если доступен).
        protocol: протокол вызова ("http", "https", "mcp").
        user_agent: заголовок User-Agent (для HTTP).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str | None = None
    request_timestamp: datetime | None = None
    request_path: str | None = None
    request_method: str | None = None
    full_url: str | None = None
    client_ip: str | None = None
    protocol: str | None = None
    user_agent: str | None = None
