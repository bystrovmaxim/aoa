# src/action_machine/system_core/__init__.py
"""
Lightweight runtime introspection helpers (types/callables and intent-scratch scanning).
"""

from __future__ import annotations

from .type_introspection import TypeIntrospection

__all__ = [
    "TypeIntrospection",
]
