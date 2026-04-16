# src/maxitor/test_domain/entities/lifecycle.py
"""Lifecycle тестовой сущности Order — отдельный файл."""

from action_machine.domain import Lifecycle


class TestOrderLifecycle(Lifecycle):
    """Простой lifecycle для графа."""

    _template = (
        Lifecycle()
        .state("new", "New").to("confirmed", "cancelled").initial()
        .state("confirmed", "Confirmed").to("shipped").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )
