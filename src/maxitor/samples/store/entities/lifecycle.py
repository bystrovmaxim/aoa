# src/maxitor/samples/store/entities/lifecycle.py
from action_machine.domain import Lifecycle


class SalesOrderLifecycle(Lifecycle):
    """Жизненный цикл заказа для демо-модели."""

    _template = (
        Lifecycle()
        .state("new", "New").to("confirmed", "cancelled").initial()
        .state("confirmed", "Confirmed").to("shipped").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )
