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


class CustomerAccountLifecycle(Lifecycle):
    """Три состояния: выдан → активен → закрыт."""

    _template = (
        Lifecycle()
        .state("provisioned", "Provisioned").to("active").initial()
        .state("active", "Active").to("closed").intermediate()
        .state("closed", "Closed").final()
    )


class SalesOrderLineLifecycle(Lifecycle):
    """Три состояния: открыта → зарезервирована → выполнена."""

    _template = (
        Lifecycle()
        .state("open", "Open").to("reserved").initial()
        .state("reserved", "Reserved").to("fulfilled").intermediate()
        .state("fulfilled", "Fulfilled").final()
    )


class AuditLogEntryLifecycle(Lifecycle):
    """Три состояния: запись → индексация → хранение."""

    _template = (
        Lifecycle()
        .state("written", "Written").to("indexed").initial()
        .state("indexed", "Indexed").to("retained").intermediate()
        .state("retained", "Retained").final()
    )
