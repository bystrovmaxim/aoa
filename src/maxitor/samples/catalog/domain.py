# src/maxitor/samples/catalog/domain.py
"""Маркер bounded context «каталог и цены»."""

from action_machine.domain import BaseDomain


class CatalogDomain(BaseDomain):
    name = "catalog"
    description = "Product catalog and merchandising slice for the sample app"
