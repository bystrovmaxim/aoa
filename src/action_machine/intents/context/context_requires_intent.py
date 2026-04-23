# src/action_machine/intents/context/context_requires_intent.py
"""
Context-requires intent marker.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ContextRequiresIntent`` is marker mixin indicating that a class may use
``@context_requires`` on aspects, error handlers, and compensators.

═══════════════════════════════════════════════════════════════════════════════
BASEACTION MRO INTENTS
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` inherits multiple intent markers. Each marker defines one
grammar segment: which decorators are allowed and what tooling may rely on
via ``issubclass``:

    ActionMetaIntent       -> @meta
    CheckRolesIntent             -> @check_roles
    DependsIntent       -> @depends
    CheckerIntent          -> result_* checkers
    AspectIntent           -> @regular_aspect / @summary_aspect
    CompensateIntent       -> @compensate
    ConnectionIntent       -> @connection
    OnErrorIntent          -> @on_error
    ContextRequiresIntent  -> @context_requires

Common pattern: empty marker classes without behavior; ``issubclass`` links
type to declaration contract.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        ActionMetaIntent,
        CheckRolesIntent,
        DependsIntent[object],
        CheckerIntent,
        AspectIntent,
        CompensateIntent,
        ConnectionIntent,
        OnErrorIntent,
        ContextRequiresIntent,        <- intent: @context_requires grammar
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Permission check")
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def check_permissions_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            ...

    # Inspectors collect ``_required_context_keys`` into facet snapshots.
    # Runtime:
    #   1. Reads aspect_meta.context_keys -> frozenset({"user.user_id", "user.roles"}).
    #   2. Creates ContextView(context, aspect_meta.context_keys).
    #   3. Passes ctx_view as 6th argument.

"""


class ContextRequiresIntent:
    """
    AI-CORE-BEGIN
    ROLE: Context-access grammar marker for action classes.
    CONTRACT: Include in MRO when using @context_requires (e.g. via BaseAction).
    INVARIANTS: Pure marker with no runtime behavior/state.
    AI-CORE-END
    """

    pass
