# src/maxitor/samples/catalog/entities/catalog_product_lifecycle.py
"""Класс жизненного цикла для товарной строки каталога (sample)."""

from action_machine.domain import Lifecycle


class CatalogProductLifecycle(Lifecycle):
    """Три состояния: черновик → в продаже → снят."""

    _template = (
        Lifecycle()
        .state("draft", "Draft").to("active").initial()
        .state("active", "Active").to("retired").intermediate()
        .state("retired", "Retired").final()
    )
