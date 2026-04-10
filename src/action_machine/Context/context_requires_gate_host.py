# src/action_machine/context/context_requires_gate_host.py
"""
ContextRequiresGateHost — marker mixin для декоратора @context_requires.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ContextRequiresGateHost — миксин-маркер, обозначающий, что класс
поддерживает декоратор @context_requires на своих methodах-аспектах
и обработчиках ошибок. Наследуется BaseAction.

Наличие ContextRequiresGateHost в MRO класса документирует контракт:
«этот класс может содержать methodы с @context_requires, и машина
создаст для них ContextView с разрешёнными полями contextа».

MetadataBuilder при сборке метаданных проверяет: если method имеет
атрибут _required_context_keys, класс обязан наследовать
ContextRequiresGateHost. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ВЗАИМОДЕЙСТВИЕ С ДРУГИМИ ГЕЙТХОСТАМИ
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует десять маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost       → разрешает и ТРЕБУЕТ @meta
    RoleGateHost             → разрешает @check_roles
    DependencyGateHost       → разрешает @depends
    CheckerGateHost          → разрешает checkerы (@result_string и др.)
    AspectGateHost           → разрешает @regular_aspect и @summary_aspect
    CompensateGateHost       → разрешает @compensate
    ConnectionGateHost       → разрешает @connection
    OnErrorGateHost          → разрешает @on_error
    ContextRequiresGateHost  → разрешает @context_requires

Все миксины следуют единому паттерну: пустой класс без логики,
служащий проверочным маркером для issubclass().

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaGateHost,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        CompensateGateHost,
        ConnectionGateHost,
        OnErrorGateHost,
        ContextRequiresGateHost,        ← маркер: разрешает @context_requires
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Проверка прав")
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def check_permissions_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            ...

    # MetadataBuilder при сборке:
    #   1. Находит _required_context_keys на methodе check_permissions_aspect.
    #   2. Checks issubclass(CreateOrderAction, ContextRequiresGateHost) → True.
    #   3. Записывает context_keys в snapshot аспекта.
    #
    # ActionProductMachine при вызове аспекта:
    #   1. Читает aspect_meta.context_keys → frozenset({"user.user_id", "user.roles"}).
    #   2. Создаёт ContextView(context, aspect_meta.context_keys).
    #   3. Передаёт ctx_view как 6-й аргумент.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует ContextRequiresGateHost — любой Action
    # автоматически поддерживает @context_requires на своих methodах.

    # Аспект с доступом к contextу:
    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user, "from_ip": ip}

    # Аспект без доступа к contextу (стандартная signature):
    @regular_aspect("Расчёт суммы")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}
"""

from __future__ import annotations

from typing import Any


class ContextRequiresGateHost:
    """
    Marker mixin, обозначающий поддержку декоратора @context_requires.

    Class, наследующий ContextRequiresGateHost, может содержать methodы
    с @context_requires. MetadataBuilder при сборке метаданных проверяет
    наличие этого миксина в MRO для каждого methodа с _required_context_keys.

    Миксин не содержит логики, полей или methodов. Его единственная
    функция — служить проверочным маркером для issubclass() в валидаторах
    MetadataBuilder и обеспечивать единообразие с остальными гейтхостами
    системы.
    """

    pass


def _has_any_context_keys(
    aspects: list[Any],
    error_handlers: list[Any],
    compensators: list[Any],
) -> bool:
    for aspect in aspects:
        if aspect.context_keys:
            return True
    for handler in error_handlers:
        if handler.context_keys:
            return True
    for comp in compensators:
        if comp.context_keys:
            return True
    return False


def require_context_requires_gate_host_marker(
    cls: type,
    aspects: list[Any],
    error_handlers: list[Any],
    compensators: list[Any],
) -> None:
    """Есть @context_requires на methodах → класс должен наследовать ContextRequiresGateHost."""
    if _has_any_context_keys(aspects, error_handlers, compensators) and not issubclass(
        cls, ContextRequiresGateHost
    ):
        methods_with_ctx: list[str] = []
        for a in aspects:
            if a.context_keys:
                methods_with_ctx.append(a.method_name)
        for h in error_handlers:
            if h.context_keys:
                methods_with_ctx.append(h.method_name)
        for c in compensators:
            if c.context_keys:
                methods_with_ctx.append(c.method_name)
        methods_str = ", ".join(methods_with_ctx)
        raise TypeError(
            f"Класс {cls.__name__} содержит методы с @context_requires "
            f"({methods_str}), но не наследует ContextRequiresGateHost. "
            f"Декоратор @context_requires разрешён только на классах, "
            f"наследующих ContextRequiresGateHost. Используйте BaseAction "
            f"или добавьте ContextRequiresGateHost в цепочку наследования."
        )
