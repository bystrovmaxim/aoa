# packages/aoa-action-machine/src/aoa/action_machine/resources/data_source_resolver.py
"""
Which data source a resource class names, read from the type arguments of its bases.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource names its data source as the type argument of a generic resource base:
``class OrdersStorage(PostgresStorage[ShopDataSource])``. Python keeps that argument
in ``__orig_bases__`` but does not check it against the parameter's bound, so this module
reads it and checks it when the resource class is created.

═══════════════════════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════════════════════

- A data source argument lies within the bound of the parameter it fills:
  ``PostgresStorage[D: PostgresDataSource]`` takes no ``RedisDataSource``.
- A resource hierarchy names at most one data source.
- A resource that inherits a base without a type argument has no data source.
"""

from __future__ import annotations

from typing import Any, get_args, get_origin

from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.resources.base_data_source import BaseDataSource


def _is_data_source(value: Any) -> bool:
    """True for a data source class; ``BaseDataSource`` itself is the default of a resource that names none."""
    return isinstance(value, type) and issubclass(value, BaseDataSource) and value is not BaseDataSource


def _own_data_source_arguments(cls: type) -> list[tuple[Any, Any, type[BaseDataSource]]]:
    """``(generic base, its parameter, data source)`` for each data source argument in ``cls``'s own bases."""
    found: list[tuple[Any, Any, type[BaseDataSource]]] = []
    for base in cls.__dict__.get("__orig_bases__", ()):
        origin = get_origin(base)
        parameters = getattr(origin, "__parameters__", ())
        for parameter, argument in zip(parameters, get_args(base), strict=False):
            if _is_data_source(argument):
                found.append((origin, parameter, argument))
    return found


def resolve_data_source(cls: type) -> type[BaseDataSource] | None:
    """
    Return the data source ``cls`` names through its bases, or ``None`` when it names none.

    Args:
        cls: a resource class.
    """
    for klass in cls.__mro__:
        arguments = _own_data_source_arguments(klass)
        if arguments:
            return arguments[0][2]
    return None


def check_data_source_arguments(cls: type) -> None:
    """
    Refuse a data source argument outside its parameter's bound, and a second data source in the hierarchy.

    Raises:
        DataSourceDeclarationError: naming the resource, the data source and what it needs.
    """
    named: set[type[BaseDataSource]] = set()
    for klass in cls.__mro__:
        for origin, parameter, data_source in _own_data_source_arguments(klass):
            bound = getattr(parameter, "__bound__", None)
            if isinstance(bound, type) and not issubclass(data_source, bound):
                raise DataSourceDeclarationError(
                    f"{cls.__name__}: {origin.__name__}[{data_source.__name__}] needs a data source of the kind "
                    f"{bound.__name__}; {data_source.__name__} is not one."
                )
            named.add(data_source)
    if len(named) > 1:
        names = ", ".join(sorted(source.__name__ for source in named))
        raise DataSourceDeclarationError(f"{cls.__name__}: a resource has one data source; its bases name {names}.")
