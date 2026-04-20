# src/graph/qualified_name.py
"""
cls_qualified_dotted_id — stable ``module.qualname`` string for Python types.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a single shared implementation for interchange IDs, facet ``node_name``
bodies, and other graph keys that must match the dotted import path of a class
(including nested classes via ``__qualname__``).
"""

from __future__ import annotations


def cls_qualified_dotted_id(cls: type) -> str:
    """
    Full dotted path for a class: ``<module>.<qualname>``.

    The same string policy as :meth:`BaseIntentInspector._make_node_name`
    without a suffix. For ``__main__`` or a missing ``__module__``, only
    ``__qualname__`` is returned.

    Args:
        cls: A ``type`` object (usually a declared class).

    Returns:
        Stable dotted class path for graph tooling and interchange payloads.
    """
    module = getattr(cls, "__module__", None)
    if module and module != "__main__":
        return f"{module}.{cls.__qualname__}"
    return cls.__qualname__
