# src/action_machine/compensate/__init__.py
"""
Пакет: compensate — механизм компенсации (Saga) для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Пакет предоставляет декоратор @compensate для объявления methodов-compensatorов
в Action-классах. Компенсатор — это method, который откатывает побочные эффекты
одного regular-аспекта при возникновении ошибки в конвейере (паттерн Saga).

В распределённых системах и длительных бизнес-процессах невозможно использовать
двухфазный коммит. Вместо этого каждая операция имеет компенсирующую операцию,
которая отменяет её эффекты. При сбое на любом шаге выполняются компенсации
уже выполненных операций в обратном порядке.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

- Декоратор ``@compensate`` пишет ``_compensate_meta`` на method.
- ``CompensateGateHostInspector`` при ``GateCoordinator.build()`` формирует
  facet ``compensator``; снимок читают как ``get_snapshot(cls, \"compensator\")``.
- ``ActionProductMachine._rollback_saga()`` разматывает стек ``SagaFrame`` и
  вызывает compensatorы (исполнение идёт по scratch/runtime, не через координатор).

CompensateGateHostInspector (через локальный сборщик `_collect_compensators`) собирает
эти атрибуты из vars(cls) и формирует snapshot CompensatorMeta.
Модуль compensate_gate_host проверяет инварианты при сборке метаданных.
ActionProductMachine использует CompensatorMeta при размотке стека SagaFrame.

═══════════════════════════════════════════════════════════════════════════════
КЛЮЧЕВЫЕ ПРАВИЛА
═══════════════════════════════════════════════════════════════════════════════

1. Компенсаторы определяются только для regular-аспектов (не для summary).
2. Для одного аспекта — не более одного compensatorа.
3. Компенсаторы НЕ наследуются — собираются только из vars(cls).
4. Ошибки compensatorов молчаливые — не прерывают размотку стека.
5. При rollup=True compensatorы не вызываются.
6. Имя methodа-compensatorа заканчивается на "_compensate".
7. Компенсатор — async def.
8. Возвращаемое значение compensatorа игнорируется.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА КОМПЕНСАТОРА
═══════════════════════════════════════════════════════════════════════════════

Без @context_requires (7 parameters):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error)

С @context_requires (8 parameters):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error, ctx)

Параметры:
    params       — входные параметры действия (frozen BaseParams).
    state_before — состояние ДО выполнения аспекта (frozen BaseState).
    state_after  — состояние ПОСЛЕ аспекта (frozen BaseState или None).
                   None означает: checker отклонил результат, но побочный
                   эффект мог произойти.
    box          — ToolsBox (тот же экземпляр, что у аспектов).
    connections  — словарь ресурсных менеджеров.
    error        — исключение, вызвавшее размотку стека.
    ctx          — ContextView (только при @context_requires).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.compensate import compensate

    class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

        @regular_aspect("Charge payment")
        async def process_payment_aspect(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.user_id, state.amount)
            return {"txn_id": txn_id}

        @compensate("process_payment_aspect", "Rollback платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections, error):
            if state_after is None:
                return  # checker отклонил — txn_id неизвестен
            try:
                payment = box.resolve(PaymentService)
                await payment.refund(state_after.txn_id)
            except Exception as e:
                await box.log.error(
                    "Не удалось откатить платёж {%var.txn}: {%var.err}",
                    txn=state_after.txn_id, err=str(e),
                )


AI-CORE-BEGIN
ROLE: module __init__
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from action_machine.compensate.compensate_decorator import compensate
from action_machine.compensate.compensate_gate_host import CompensateGateHost

__all__ = [
    "CompensateGateHost",
    "compensate",
]
