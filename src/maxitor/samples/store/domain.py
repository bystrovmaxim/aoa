# src/maxitor/samples/store/domain.py
"""Маркер bounded context «магазин / оформление заказа»."""

from action_machine.domain import BaseDomain


class StoreDomain(BaseDomain):
    name = "store"
    description = "Sample storefront: checkout, entities, plugins, and persistence stubs"
