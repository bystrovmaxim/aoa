# packages/aoa-action-machine/src/aoa/action_machine/resources/base_data_source.py
"""
BaseDataSource — one database or other store that several resources share.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource is often a part of a database, not the whole of it. A data source names
that database, so the model knows which resources work with one store: entities of
those resources may relate to each other, because a join between their tables is
ordinary. A data source keeps what the resources share — the connection parameters
and the pool, when there is one — while each resource keeps its own transaction.

``BaseDataSource`` itself promises nothing about connections, so it fits any store:
a database with a pool or without, an external service, something a controller owns.
A kind of data source (``PostgresDataSource``) gives its resources a way to get a
connection; an application derives its own data source from that kind.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- A data source declares ``@meta(description=...)`` and no domain: it is physical, and
  resources of several domains may share it. In the graph it belongs to the application.
- Its class name ends in ``DataSource``.
- It is not a resource: an action cannot depend on it, so it cannot go around a resource.
- A resource names it as the type argument of its base: ``PostgresResource[ShopDataSource]``.
  A data source is optional; a resource without one works on its own.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

::

    @meta(description="Main shop database")
    class ShopDataSource(PostgresDataSource): ...

    @meta(description="Orders", domain=SalesDomain)
    class OrdersResource(PostgresResource[ShopDataSource]): ...
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.meta.meta_intent import MetaIntent

DATA_SOURCE_SUFFIX = "DataSource"
"""The ending every data source class name carries."""


@exclude_graph_model
class BaseDataSource(ABC, MetaIntent):
    """
    AI-CORE-BEGIN
    ROLE: Root of the stores several resources may share.
    CONTRACT: ``@meta(description=...)`` without a domain; the class name ends in ``DataSource``; no methods of its own.
    INVARIANTS: Not depends-eligible; belongs to the application, not to a domain.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Refuse a data source class whose name does not end in ``DataSource``."""
        super().__init_subclass__(**kwargs)
        if not cls.__name__.endswith(DATA_SOURCE_SUFFIX):
            raise NamingSuffixError(f"{cls.__name__}: a data source class name ends in '{DATA_SOURCE_SUFFIX}'.")
