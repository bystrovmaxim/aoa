# src/maxitor/samples/messaging/entities/outbox_lifecycle.py
"""Класс жизненного цикла для строки outbox (sample)."""

from action_machine.domain import Lifecycle


class OutboxMessageLifecycle(Lifecycle):
    """Три состояния: ожидание → опубликовано → обработано."""

    _template = (
        Lifecycle()
        .state("pending", "Pending").to("published").initial()
        .state("published", "Published").to("consumed").intermediate()
        .state("consumed", "Consumed").final()
    )
