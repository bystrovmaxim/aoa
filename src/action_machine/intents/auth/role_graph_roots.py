# src/action_machine/intents/auth/role_graph_roots.py
"""
Canonical ``role_class`` graph anchors for interchange topology.

Only ``ApplicationRole`` is materialized as a ``role_class`` vertex. The
``SystemRole`` branch (``NoneRole``, ``AnyRole``, …) is not a separate graph
node; ``requires_role`` edges use the same anchor (see
:func:`role_class_topology_anchor`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from action_machine.intents.auth.application_role import ApplicationRole

if TYPE_CHECKING:
    pass

ROLE_CLASS_GRAPH_ROOTS: frozenset[type] = frozenset({ApplicationRole})


def role_class_topology_anchor(role_cls: type) -> type:
    """
    Map any ``BaseRole`` subtype to the single ``role_class`` graph anchor.

    Interchange exposes one ``role_class`` node (``ApplicationRole``). Sentinel
    and application concrete types all fold onto it for ``requires_role`` edges;
    use ``edge_meta`` on those edges to recover declared ``@check_roles`` types.
    """
    return ApplicationRole
