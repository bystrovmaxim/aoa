# src/action_machine/graph/vertex_id.py
"""
Parse **composite vertex ids** (``graph.md`` v4.1 §2.2).

Deterministic parsing for checker ids ``{host}.{method}:{field}`` and for
host-element ids ``{host}.{element}`` used by aspects, compensators, and similar
vertices.
"""

from __future__ import annotations


def split_checker_vertex_id(vertex_id: str) -> tuple[str, str, str]:
    """
    Split a checker vertex id ``{host_qualname}.{method_name}:{field_name}``.

    Raises:
        ValueError: if the id does not contain exactly one ``:`` or parts are empty.
    """
    if vertex_id.count(":") != 1:
        msg = f"checker vertex id must contain exactly one ':': {vertex_id!r}"
        raise ValueError(msg)
    left, field_name = vertex_id.split(":", 1)
    if not left or not field_name:
        msg = f"checker vertex id has empty host/method or field: {vertex_id!r}"
        raise ValueError(msg)
    if "." not in left:
        msg = f"checker vertex id missing '.' before ':': {vertex_id!r}"
        raise ValueError(msg)
    host_qualname, method_name = left.rsplit(".", 1)
    if not host_qualname or not method_name:
        msg = f"checker vertex id has empty host or method: {vertex_id!r}"
        raise ValueError(msg)
    return host_qualname, method_name, field_name


def split_host_element_vertex_id(vertex_id: str) -> tuple[str, str]:
    """
    Split ``{host_qualname}.{element_name}`` (aspect, compensator, subscription, …).

    Raises:
        ValueError: if there is no separating dot or an empty part.
    """
    if ":" in vertex_id:
        msg = (
            "host-element vertex id must not contain ':' "
            f"(use split_checker_vertex_id for checkers): {vertex_id!r}"
        )
        raise ValueError(msg)
    if "." not in vertex_id:
        msg = f"host-element vertex id must contain '.': {vertex_id!r}"
        raise ValueError(msg)
    host_qualname, element_name = vertex_id.rsplit(".", 1)
    if not host_qualname or not element_name:
        msg = f"host-element vertex id has empty host or element: {vertex_id!r}"
        raise ValueError(msg)
    return host_qualname, element_name
