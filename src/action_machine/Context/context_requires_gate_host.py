# src/action_machine/context/context_requires_gate_host.py
"""
ContextRequiresGateHost — маркерный миксин для декоратора @context_requires.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ContextRequiresGateHost — миксин-маркер, обозначающий, что класс
поддерживает декоратор @context_requires на своих методах-аспектах
и обработчиках ошибок. Наследуется BaseAction.

Наличие ContextRequiresGateHost в MRO класса документирует контракт:
«этот класс может содержать методы с @context_requires, и машина
создаст для них ContextView с разрешёнными полями контекста».

MetadataBuilder при сборке метаданных проверяет: если метод имеет
атрибут _required_context_keys, класс обязан наследовать
ContextRequiresGateHost. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ВЗАИМОДЕЙСТВИЕ С ДРУГИМИ ГЕЙТХОСТАМИ
═══════════════════════════════════════════════════════════════════════════════

BaseAction наследует восемь маркерных миксинов, каждый из которых
разрешает применение соответствующего декоратора:

    ActionMetaGateHost       → разрешает и ТРЕБУЕТ @meta
    RoleGateHost             → разрешает @check_roles
    DependencyGateHost       → разрешает @depends
    CheckerGateHost          → разрешает чекеры (@result_string и др.)
    AspectGateHost           → разрешает @regular_aspect и @summary_aspect
    ConnectionGateHost       → разрешает @connection
    OnErrorGateHost          → разрешает @on_error
    ContextRequiresGateHost  → разрешает @context_requires

Все миксины следуют единому паттерну: пустой класс без логики,
служащий проверочным маркером для issubclass().

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaGateHost,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
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
    #   1. Находит _required_context_keys на методе check_permissions_aspect.
    #   2. Проверяет issubclass(CreateOrderAction, ContextRequiresGateHost) → True.
    #   3. Записывает context_keys в AspectMeta.
    #
    # ActionProductMachine при вызове аспекта:
    #   1. Читает aspect_meta.context_keys → frozenset({"user.user_id", "user.roles"}).
    #   2. Создаёт ContextView(context, aspect_meta.context_keys).
    #   3. Передаёт ctx_view как 6-й аргумент.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует ContextRequiresGateHost — любой Action
    # автоматически поддерживает @context_requires на своих методах.

    # Аспект с доступом к контексту:
    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user, "from_ip": ip}

    # Аспект без доступа к контексту (стандартная сигнатура):
    @regular_aspect("Расчёт суммы")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}
"""


class ContextRequiresGateHost:
    """
    Маркерный миксин, обозначающий поддержку декоратора @context_requires.

    Класс, наследующий ContextRequiresGateHost, может содержать методы
    с @context_requires. MetadataBuilder при сборке метаданных проверяет
    наличие этого миксина в MRO для каждого метода с _required_context_keys.

    Миксин не содержит логики, полей или методов. Его единственная
    функция — служить проверочным маркером для issubclass() в валидаторах
    MetadataBuilder и обеспечивать единообразие с остальными гейтхостами
    системы.
    """

    pass
