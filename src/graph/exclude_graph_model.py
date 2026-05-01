# src/graph/exclude_graph_model.py
"""
Opt-out markers for interchange graph row emission (:class:`~graph.base_graph_node_inspector.BaseGraphNodeInspector`).
"""

from __future__ import annotations

# Class-level sentinel read by ``BaseGraphNodeInspector._should_skip_axis_host``.
_EXCLUDE_GRAPH_MODEL_KEY = "__graph_exclude_graph_model__"


def exclude_graph_model[T: type](cls: T) -> T:
    """
    Mark a host class so axis inspectors skip it when assembling interchange nodes.

    **Only classes** — typically implementation proxies without coordinator ``@meta``.

    Repeated application is idempotent (flag remains truthy).
    """
    if not isinstance(cls, type):
        msg = (
            f"{exclude_graph_model.__qualname__} applies only to classes, "
            f"got {type(cls).__qualname__!r}"
        )
        raise TypeError(msg)
    setattr(cls, _EXCLUDE_GRAPH_MODEL_KEY, True)
    return cls


def excluded_from_graph_model(host: object) -> bool:
    """
    ``True`` when ``host`` is a ``type`` directly marked with :func:`exclude_graph_model`.

    The flag is read from the class's own namespace only; subclasses do not inherit
    exclusion (each class that should be skipped must be decorated).
    """
    return isinstance(host, type) and bool(host.__dict__.get(_EXCLUDE_GRAPH_MODEL_KEY, False))


__all__ = ["exclude_graph_model", "excluded_from_graph_model"]
