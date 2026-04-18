# src/maxitor/samples/store/__init__.py
"""Основной bounded context демо-приложения: заказы, аудит, полный набор декораторов на действии."""

from maxitor.samples.store.domain import StoreDomain

__all__ = ["StoreDomain"]
