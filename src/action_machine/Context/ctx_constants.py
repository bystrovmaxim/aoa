# src/action_machine/context/ctx_constants.py
"""
Константы путей контекста для декоратора @context_requires.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит вложенную структуру констант Ctx, описывающую все
стандартные поля контекста выполнения (Context). Каждая константа —
строка dot-path, которая передаётся в @context_requires и используется
для доступа через ContextView.get().

Константы строго соответствуют реальным полям классов UserInfo,
RequestInfo и RuntimeInfo. Никаких выдуманных путей — только то,
что реально существует в коде.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════

    Ctx.User      → поля UserInfo (user_id, roles)
    Ctx.Request   → поля RequestInfo (trace_id, request_timestamp, request_path,
                    request_method, full_url, client_ip, protocol, user_agent)
    Ctx.Runtime   → поля RuntimeInfo (hostname, service_name, service_version,
                    container_id, pod_name)

Каждая константа — строка вида "компонент.поле", например:
    Ctx.User.user_id    == "user.user_id"
    Ctx.Request.trace_id == "request.trace_id"
    Ctx.Runtime.hostname == "runtime.hostname"

Путь соответствует навигации через Context.resolve():
    context.resolve("user.user_id")      → context.user.user_id
    context.resolve("request.trace_id")  → context.request.trace_id

═══════════════════════════════════════════════════════════════════════════════
РАСШИРЕНИЕ КОМПОНЕНТОВ КОНТЕКСТА
═══════════════════════════════════════════════════════════════════════════════

UserInfo, RequestInfo и RuntimeInfo расширяются через наследование
с явно объявленными полями. Константы Ctx покрывают стандартные поля
с автодополнением IDE. Для кастомных полей наследников используются
строковые пути напрямую:

    class BillingUserInfo(UserInfo):
        billing_plan: str = "free"

    @context_requires(Ctx.User.user_id, "user.billing_plan")
    async def billing_aspect(self, params, state, box, connections, ctx):
        plan = ctx.get("user.billing_plan")
        ...

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx, context_requires

    @regular_aspect("Проверка прав")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def check_permissions_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        roles = ctx.get(Ctx.User.roles)
        ...

    # Смесь констант и строковых путей для кастомных полей:
    @regular_aspect("Биллинг")
    @context_requires(Ctx.User.user_id, "user.billing_plan")
    async def billing_aspect(self, params, state, box, connections, ctx):
        plan = ctx.get("user.billing_plan")
        ...
"""


class _UserFields:
    """
    Константы путей для полей UserInfo внутри Context.

    Каждый атрибут — строка dot-path вида "user.<имя_поля>",
    соответствующая реальному полю класса UserInfo.
    """

    user_id: str = "user.user_id"
    """ID пользователя. Тип в UserInfo: str | None."""

    roles: str = "user.roles"
    """Список ролей пользователя. Тип в UserInfo: list[str]."""


class _RequestFields:
    """
    Константы путей для полей RequestInfo внутри Context.

    Каждый атрибут — строка dot-path вида "request.<имя_поля>",
    соответствующая реальному полю класса RequestInfo.
    """

    trace_id: str = "request.trace_id"
    """Уникальный ID запроса для трассировки. Тип в RequestInfo: str | None."""

    request_timestamp: str = "request.request_timestamp"
    """Время получения запроса. Тип в RequestInfo: datetime | None."""

    request_path: str = "request.request_path"
    """Путь эндпоинта или имя инструмента. Тип в RequestInfo: str | None."""

    request_method: str = "request.request_method"
    """HTTP-метод или "tool_call". Тип в RequestInfo: str | None."""

    full_url: str = "request.full_url"
    """Полный URL запроса. Тип в RequestInfo: str | None."""

    client_ip: str = "request.client_ip"
    """IP-адрес клиента. Тип в RequestInfo: str | None."""

    protocol: str = "request.protocol"
    """Протокол вызова ("http", "https", "mcp"). Тип в RequestInfo: str | None."""

    user_agent: str = "request.user_agent"
    """Заголовок User-Agent. Тип в RequestInfo: str | None."""


class _RuntimeFields:
    """
    Константы путей для полей RuntimeInfo внутри Context.

    Каждый атрибут — строка dot-path вида "runtime.<имя_поля>",
    соответствующая реальному полю класса RuntimeInfo.
    """

    hostname: str = "runtime.hostname"
    """Имя хоста или контейнера. Тип в RuntimeInfo: str | None."""

    service_name: str = "runtime.service_name"
    """Название сервиса. Тип в RuntimeInfo: str | None."""

    service_version: str = "runtime.service_version"
    """Версия сервиса. Тип в RuntimeInfo: str | None."""

    container_id: str = "runtime.container_id"
    """ID Docker-контейнера. Тип в RuntimeInfo: str | None."""

    pod_name: str = "runtime.pod_name"
    """Имя пода Kubernetes. Тип в RuntimeInfo: str | None."""


class Ctx:
    """
    Вложенная структура констант для декларации доступа к полям контекста.

    Используется в декораторе @context_requires для указания,
    какие поля контекста нужны аспекту или обработчику ошибок.

    Три группы полей соответствуют трём компонентам Context:
        Ctx.User    → UserInfo    (пользователь)
        Ctx.Request → RequestInfo (входящий запрос)
        Ctx.Runtime → RuntimeInfo (среда выполнения)

    Каждая константа — строка dot-path. IDE автодополняет имена,
    mypy проверяет типы (все — str), опечатка в имени поля
    обнаруживается статически.

    Пример:
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def my_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            trace = ctx.get(Ctx.Request.trace_id)
    """

    User = _UserFields
    """Поля компонента UserInfo контекста."""

    Request = _RequestFields
    """Поля компонента RequestInfo контекста."""

    Runtime = _RuntimeFields
    """Поля компонента RuntimeInfo контекста."""
