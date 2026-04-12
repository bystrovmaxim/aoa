# src/action_machine/context/context_requires_intent.py
"""
ContextRequiresIntent — marker mixin для декоратора @context_requires.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ContextRequiresIntent — миксин-маркер, обозначающий, что класс
поддерживает декоратор @context_requires на своих methodах-аспектах
и обработчиках ошибок. Наследуется BaseAction.

Наличие ContextRequiresIntent в MRO класса документирует контракт:
«этот класс участвует в грамматике @context_requires и может содержать
methodы с этим декоратором; машина построит для них ContextView только
с теми полями contextа, которые явно запрошены декоратором».

MetadataBuilder при сборке метаданных проверяет: если method имеет
атрибут _required_context_keys, класс обязан наследовать
ContextRequiresIntent. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
НАМЕРЕНИЯ В MRO BaseAction И СВЯЗАННАЯ ГРАММАТИКА
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует десять маркеров намерения (Intent): каждый задаёт
фрагмент грамматики типа — какие декораторы и scratch допустимы и что
фреймворк проверит при сборке графа (``GateCoordinator.build()``):

    ActionMetaIntent       → намерение @meta (при аспектах — обязательно)
    RoleIntent             → намерение @check_roles
    DependencyIntent       → намерение @depends
    CheckerIntent          → намерение чекеров (@result_string и др.)
    AspectIntent           → намерение @regular_aspect и @summary_aspect
    CompensateIntent       → намерение @compensate
    ConnectionIntent       → намерение @connection
    OnErrorIntent          → намерение @on_error
    ContextRequiresIntent  → намерение @context_requires

Общий паттерн: пустой класс-маркер без логики; ``issubclass`` связывает
тип с обязательствами и валидаторами.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaIntent,
        RoleIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        CompensateIntent,
        ConnectionIntent,
        OnErrorIntent,
        ContextRequiresIntent,        ← намерение: грамматика @context_requires
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Проверка прав")
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def check_permissions_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            ...

    # MetadataBuilder при сборке:
    #   1. Находит _required_context_keys на methodе check_permissions_aspect.
    #   2. Checks issubclass(CreateOrderAction, ContextRequiresIntent) → True.
    #   3. Записывает context_keys в snapshot аспекта.
    #
    # ActionProductMachine при вызове аспекта:
    #   1. Читает aspect_meta.context_keys → frozenset({"user.user_id", "user.roles"}).
    #   2. Создаёт ContextView(context, aspect_meta.context_keys).
    #   3. Передаёт ctx_view как 6-й аргумент.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует ContextRequiresIntent — любой Action
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


class ContextRequiresIntent:
    """
    Marker mixin, обозначающий поддержку декоратора @context_requires.

    Class, наследующий ContextRequiresIntent, может содержать methodы
    с @context_requires. MetadataBuilder при сборке метаданных проверяет
    наличие этого миксина в MRO для каждого methodа с _required_context_keys.

    Миксин не содержит логики, полей или methodов. Его единственная
    функция — служить проверочным маркером для issubclass() в валидаторах
    MetadataBuilder и оставаться в одном ряду с остальными Intent-маркерами
    BaseAction.
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


def require_context_requires_intent_marker(
    cls: type,
    aspects: list[Any],
    error_handlers: list[Any],
    compensators: list[Any],
) -> None:
    """Есть @context_requires на methodах → класс должен наследовать ContextRequiresIntent."""
    if _has_any_context_keys(aspects, error_handlers, compensators) and not issubclass(
        cls, ContextRequiresIntent
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
            f"({methods_str}), но не наследует ContextRequiresIntent. "
            f"Декоратор @context_requires входит в грамматику только при "
            f"намерении ContextRequiresIntent в MRO. Используйте BaseAction "
            f"или добавьте ContextRequiresIntent в цепочку наследования."
        )
