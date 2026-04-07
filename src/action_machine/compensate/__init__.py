# src/action_machine/compensate/__init__.py
"""
Пакет: compensate — механизм компенсации (Saga) для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Пакет предоставляет декоратор @compensate для объявления методов-компенсаторов
в Action-классах. Компенсатор — это метод, который откатывает побочные эффекты
одного regular-аспекта при возникновении ошибки в конвейере (паттерн Saga).

В распределённых системах и длительных бизнес-процессах невозможно использовать
двухфазный коммит. Вместо этого каждая операция имеет компенсирующую операцию,
которая отменяет её эффекты. При сбое на любом шаге выполняются компенсации
уже выполненных операций в обратном порядке.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    Объявление                  Сборка                    Выполнение
    ──────────                  ──────                    ──────────
    @compensate(             MetadataBuilder            _rollback_saga()
      "aspect_name",         собирает                   разматывает стек
      "описание"             _compensate_meta           SagaFrame в обратном
    )                        → CompensatorMeta           порядке
    async def ...            → ClassMetadata.            и вызывает
                               compensators              компенсаторы

Декоратор @compensate записывает на метод атрибут _compensate_meta.
MetadataBuilder (metadata/collectors.py) собирает эти атрибуты из vars(cls)
и создаёт CompensatorMeta. Валидатор (metadata/validators.py) проверяет
инварианты при сборке метаданных. ActionProductMachine использует
CompensatorMeta при размотке стека SagaFrame.

═══════════════════════════════════════════════════════════════════════════════
КЛЮЧЕВЫЕ ПРАВИЛА
═══════════════════════════════════════════════════════════════════════════════

1. Компенсаторы определяются только для regular-аспектов (не для summary).
2. Для одного аспекта — не более одного компенсатора.
3. Компенсаторы НЕ наследуются — собираются только из vars(cls).
4. Ошибки компенсаторов молчаливые — не прерывают размотку стека.
5. При rollup=True компенсаторы не вызываются.
6. Имя метода-компенсатора заканчивается на "_compensate".
7. Компенсатор — async def.
8. Возвращаемое значение компенсатора игнорируется.

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА КОМПЕНСАТОРА
═══════════════════════════════════════════════════════════════════════════════

Без @context_requires (7 параметров):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error)

С @context_requires (8 параметров):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error, ctx)

Параметры:
    params       — входные параметры действия (frozen BaseParams).
    state_before — состояние ДО выполнения аспекта (frozen BaseState).
    state_after  — состояние ПОСЛЕ аспекта (frozen BaseState или None).
                   None означает: чекер отклонил результат, но побочный
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

        @regular_aspect("Списание средств")
        async def process_payment_aspect(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.user_id, state.amount)
            return {"txn_id": txn_id}

        @compensate("process_payment_aspect", "Откат платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections, error):
            if state_after is None:
                return  # чекер отклонил — txn_id неизвестен
            try:
                payment = box.resolve(PaymentService)
                await payment.refund(state_after.txn_id)
            except Exception as e:
                await box.log.error(
                    "Не удалось откатить платёж {%var.txn}: {%var.err}",
                    txn=state_after.txn_id, err=str(e),
                )
"""

from action_machine.compensate.compensate_decorator import compensate

__all__ = [
    "compensate",
]