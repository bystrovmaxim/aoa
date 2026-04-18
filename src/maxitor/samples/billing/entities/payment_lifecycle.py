# src/maxitor/samples/billing/entities/payment_lifecycle.py
"""Класс жизненного цикла для сущности платёжного события (как ``SalesOrderLifecycle`` в store)."""

from action_machine.domain import Lifecycle


class PaymentEventLifecycle(Lifecycle):
    """Три состояния: запись → проведение → архив."""

    _template = (
        Lifecycle()
        .state("recorded", "Recorded").to("settled").initial()
        .state("settled", "Settled").to("archived").intermediate()
        .state("archived", "Archived").final()
    )
