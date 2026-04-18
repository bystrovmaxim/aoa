# src/maxitor/samples/store/entities/lifecycle.py
from action_machine.domain import Lifecycle


class SalesOrderLifecycle(Lifecycle):
    """Жизненный цикл заказа для демо-модели.

    Между ``confirmed`` и ``rework`` задан **цикл** (два направленных перехода).
    В графе визуализации это две дуги ``LIFECYCLE_TRANSITION``; проверка DAG на
    эти рёбра не распространяется — цикл отображается как есть.
    """

    _template = (
        Lifecycle()
        .state("new", "New").to("confirmed", "cancelled").initial()
        .state("confirmed", "Confirmed").to("shipped", "rework").intermediate()
        .state("rework", "Rework").to("confirmed").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )
