# src/action_machine/context/context.py
"""
Context — контекст выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Context — корневой объект контекста, объединяющий информацию о пользователе
(UserInfo), входящем запросе (RequestInfo) и среде выполнения (RuntimeInfo).

Создаётся один раз на каждый запрос координатором аутентификации
(AuthCoordinator или NoAuthCoordinator) и передаётся в машину при вызове
run(). Используется для проверки ролей, логирования, трассировки и
предоставления данных аспектам через ContextView.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── Context (frozen=True, extra="forbid")
                ├── user: UserInfo
                ├── request: RequestInfo
                └── runtime: RuntimeInfo

═══════════════════════════════════════════════════════════════════════════════
FROZEN И FORBID
═══════════════════════════════════════════════════════════════════════════════

Context неизменяем после создания. Контекст запроса фиксируется один раз
при входе и не меняется в ходе выполнения конвейера. Все вложенные
компоненты (UserInfo, RequestInfo, RuntimeInfo) тоже frozen.

Произвольные поля запрещены (extra="forbid"). Расширение — только через
наследование с явными полями или через расширение вложенных компонентов:

    class TenantContext(Context):
        tenant_id: str = "default"

═══════════════════════════════════════════════════════════════════════════════
АНОНИМНЫЙ КОНТЕКСТ
═══════════════════════════════════════════════════════════════════════════════

Context() без аргументов создаёт анонимный контекст: пустой UserInfo
(user_id=None, roles=[]), пустой RequestInfo и пустой RuntimeInfo.
Используется NoAuthCoordinator для открытых API.

═══════════════════════════════════════════════════════════════════════════════
DOT-PATH НАВИГАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Context наследует resolve() от BaseSchema, что позволяет обходить
вложенные компоненты через dot-path:

    context.resolve("user.user_id")           → "agent_123"
    context.resolve("user.roles")             → ["admin", "user"]
    context.resolve("request.trace_id")       → "abc-123"
    context.resolve("request.client_ip")      → "192.168.1.1"
    context.resolve("runtime.hostname")       → "pod-xyz-123"
    context.resolve("runtime.service_version") → "1.2.3"

Это используется ContextView для предоставления данных аспектам
с @context_requires и VariableSubstitutor для шаблонов логирования
({%context.user.user_id}).

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП В АСПЕКТАХ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к Context из аспекта невозможен. ToolsBox не предоставляет
публичного свойства context. Единственный путь — через @context_requires
и ContextView:

    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)     # → "agent_123"
        ip = ctx.get(Ctx.Request.client_ip)       # → "192.168.1.1"
        return {}

ContextView делегирует в context.resolve(key) для получения значений.

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    ctx = Context(
        user=UserInfo(user_id="agent_123", roles=["admin"]),
        request=RequestInfo(trace_id="abc-123"),
    )

    ctx["user"]                          # → UserInfo(...)
    ctx["request"]                       # → RequestInfo(...)
    "runtime" in ctx                     # → True
    list(ctx.keys())                     # → ["user", "request", "runtime"]
    ctx.resolve("user.user_id")          # → "agent_123"

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context.context import Context
    from action_machine.context.user_info import UserInfo
    from action_machine.context.request_info import RequestInfo
    from action_machine.context.runtime_info import RuntimeInfo

    # Полный контекст:
    ctx = Context(
        user=UserInfo(user_id="john_doe", roles=["user", "manager"]),
        request=RequestInfo(
            trace_id="abc-123",
            request_path="/api/v1/orders",
            request_method="POST",
            client_ip="192.168.1.1",
        ),
        runtime=RuntimeInfo(
            hostname="pod-xyz-123",
            service_name="orders-api",
            service_version="1.2.3",
        ),
    )

    ctx.resolve("user.user_id")           # → "john_doe"
    ctx.resolve("request.trace_id")       # → "abc-123"
    ctx.resolve("runtime.service_name")   # → "orders-api"

    # Анонимный контекст:
    anon_ctx = Context()
    anon_ctx.resolve("user.user_id")      # → None
    anon_ctx.resolve("user.roles")        # → []
"""

from pydantic import ConfigDict

from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.core.base_schema import BaseSchema


class Context(BaseSchema):
    """
    Контекст выполнения действия.

    Объединяет информацию о пользователе, запросе и среде выполнения.
    Frozen после создания. Произвольные поля запрещены.

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.
    Dot-path навигация позволяет обходить вложенные компоненты:
    context.resolve("user.user_id") → context.user.user_id.

    Атрибуты:
        user: информация о пользователе. По умолчанию — анонимный
              (user_id=None, roles=[]).
        request: метаданные входящего запроса. По умолчанию — пустой.
        runtime: информация о среде выполнения. По умолчанию — пустой.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user: UserInfo = UserInfo()
    request: RequestInfo = RequestInfo()
    runtime: RuntimeInfo = RuntimeInfo()
