# src/action_machine/intents/compensate/__init__.py
"""
Compensate package — Saga rollback mechanism for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose ``@compensate`` for declaring compensator methods in action classes.
Compensators roll back side effects of regular aspects when pipeline execution
fails, implementing Saga-style rollback semantics.

In distributed/long-running workflows where two-phase commit is impractical,
each operation provides a compensating operation. On failure, previously
executed operations are compensated in reverse order.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @compensate(...) on action method
                |
                v
    method._compensate_meta declaration
                |
                v
    CompensateIntentInspector at build()
                |
                v
    compensator facet snapshot
                |
                v
    runtime SagaFrame stack
                |
                v
    ActionProductMachine._rollback_saga() invokes compensators in reverse order

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Compensators are declared only for regular aspects (not summary aspects).
- At most one compensator may target one aspect.
- Compensators are not inherited; collection uses ``vars(cls)``.
- Compensator errors are swallowed and must not interrupt rollback unwinding.
- When ``rollup=True``, compensators are not executed.
- Compensator method names end with ``"_compensate"``.
- Compensators must be ``async def``.
- Compensator return values are ignored.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATOR SIGNATURE
═══════════════════════════════════════════════════════════════════════════════

Without ``@context_requires`` (7 parameters):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error)

With ``@context_requires`` (8 parameters):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error, ctx)

Parameters:
    params       — action input params (frozen BaseParams).
    state_before — state before aspect execution (frozen BaseState).
    state_after  — merged pipeline state after the aspect (frozen ``BaseState``)
                   when validation passed, or ``None`` when validation failed
                   after ``call()`` returned. A frame is still pushed and the
                   compensator runs on unwind with ``None``; values the aspect
                   tried to publish never reached merged state.
    box          — ToolsBox (same instance used by aspects).
    connections  — resource-manager dictionary.
    error        — exception that triggered rollback.
    ctx          — ContextView (only with ``@context_requires``).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.compensate import compensate
    from action_machine.intents.logging.channel import Channel

    class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

        @regular_aspect("Charge payment")
        async def process_payment_aspect(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.user_id, state.amount)
            return {"txn_id": txn_id}

        @compensate("process_payment_aspect", "Rollback payment")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections, error):
            if state_after is None:
                return  # checker rejected output; txn_id is unknown
            try:
                payment = box.resolve(PaymentService)
                await payment.refund(state_after.txn_id)
            except Exception as e:
                await box.critical(
                    Channel.error,
                    "Failed to roll back payment {%var.txn}: {%var.err}",
                    txn=state_after.txn_id,
                    err=str(e),
                )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Declaration-time violations raise ``TypeError``/``ValueError`` from decorator
  and intent validators.
- Runtime rollback swallows compensator failures by design.
- Compensator graph metadata is built once; runtime rollback uses cached frames.

AI-CORE-BEGIN
ROLE: Public package facade for saga compensation.
CONTRACT: Export ``compensate`` decorator and ``CompensateIntent`` marker.
INVARIANTS: Build-time metadata validation and reverse-order rollback semantics.
FLOW: declaration -> compensator facet snapshot -> runtime rollback execution.
FAILURES: declaration errors; runtime compensator errors swallowed; ``state_after``
  ``None`` after failed result validation.
EXTENSION POINTS: custom compensator methods and context-aware signatures.
AI-CORE-END
"""

from action_machine.intents.compensate.compensate_decorator import compensate
from action_machine.legacy.compensate_intent import CompensateIntent

__all__ = [
    "CompensateIntent",
    "compensate",
]
