# src/action_machine/runtime/binding/__init__.py
"""
Runtime binding helpers for ``BaseAction[P, R]`` generics — generic-arg resolution.

Result binding (:mod:`action_machine.runtime.binding.action_result_binding`) is
imported from that submodule directly to avoid cycles with intent resolvers that
reuse :func:`~action_machine.runtime.binding.action_generic_params._resolve_generic_arg`.
"""

from __future__ import annotations

from action_machine.runtime.binding.action_generic_params import (
    _resolve_forward_ref,
    _resolve_generic_arg,
)

__all__ = [
    "_resolve_forward_ref",
    "_resolve_generic_arg",
]
