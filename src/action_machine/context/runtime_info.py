# src/action_machine/context/runtime_info.py
"""
RuntimeInfo — информация о среде выполнения.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

RuntimeInfo — компонент contextа выполнения (Context), содержащий
информацию об окружении, в котором выполняется код: имя хоста, название
и версия сервиса, идентификатор контейнера, имя пода Kubernetes.

Заполняется один раз при старте приложения и затем копируется в каждый
context. Позволяет идентифицировать, на каком сервере, в какой версии
и в каком окружении выполняется действие. Особенно полезно при
горизонтальном масштабировании и анализе логов.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── RuntimeInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
FROZEN И FORBID
═══════════════════════════════════════════════════════════════════════════════

RuntimeInfo неизменяем после создания. Информация о среде фиксируется
при старте приложения и не меняется на протяжении жизни процесса.

Произвольные поля запрещены (extra="forbid"). Если конкретному проекту
нужны дополнительные данные о среде (region, availability_zone,
cluster_name), создаётся наследник с явно объявленными полями:

    class CloudRuntimeInfo(RuntimeInfo):
        region: str | None = None
        availability_zone: str | None = None
        cluster_name: str | None = None

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП В АСПЕКТАХ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к RuntimeInfo из аспекта невозможен. Единственный путь —
через @context_requires и ContextView:

    @regular_aspect("Диагностика")
    @context_requires(Ctx.Runtime.hostname, Ctx.Runtime.service_version)
    async def diagnostics_aspect(self, params, state, box, connections, ctx):
        host = ctx.get(Ctx.Runtime.hostname)              # → "pod-xyz-123"
        version = ctx.get(Ctx.Runtime.service_version)    # → "1.2.3"
        return {}

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    runtime = RuntimeInfo(hostname="pod-xyz-123", service_name="orders-api")

    runtime["hostname"]          # → "pod-xyz-123"
    "service_name" in runtime    # → True
    list(runtime.keys())         # → ["hostname", "service_name", ...]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    runtime = RuntimeInfo(
        hostname="pod-xyz-123",
        service_name="orders-api",
        service_version="1.2.3",
        container_id="abc123def456",
        pod_name="orders-api-7b9f4d-x2k",
    )

    runtime["hostname"]                  # → "pod-xyz-123"
    runtime.resolve("service_version")   # → "1.2.3"
    runtime.model_dump()                 # → {"hostname": "pod-xyz-123", ...}

    # Расширение через наследование:
    class CloudRuntimeInfo(RuntimeInfo):
        region: str | None = None
        cluster_name: str | None = None

    runtime = CloudRuntimeInfo(
        hostname="pod-xyz-123",
        service_name="orders-api",
        service_version="1.2.3",
        region="eu-west-1",
        cluster_name="production-main",
    )
"""

from pydantic import ConfigDict

from action_machine.core.base_schema import BaseSchema


class RuntimeInfo(BaseSchema):
    """
    Информация о среде выполнения.

    Frozen после создания. Произвольные поля запрещены.
    Расширение — только через наследование с явными полями.

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.

    Атрибуты:
        hostname: имя хоста (контейнера или сервера).
        service_name: название сервиса (например, "orders-api").
        service_version: версия сервиса (например, "1.2.3").
        container_id: идентификатор Docker-контейнера (если есть).
        pod_name: имя пода в Kubernetes (если есть).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hostname: str | None = None
    service_name: str | None = None
    service_version: str | None = None
    container_id: str | None = None
    pod_name: str | None = None
