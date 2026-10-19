# specs/011-role-mode-declaration/evidence/probes/typecheck_probe.py
"""Probe: does mypy accept ``isinstance(mode, type)`` on a ``RoleMode`` parameter."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

_RT = TypeVar("_RT", bound=type)


class RoleMode(Enum):
    """Four lifecycle modes."""

    ALIVE = "alive"
    DEPRECATED = "deprecated"
    SILENCED = "silenced"
    UNUSED = "unused"


def role_mode(mode: RoleMode) -> Callable[[_RT], _RT]:
    """Attach the mode to a class, refusing anything that is not a member."""
    if isinstance(mode, type):
        raise TypeError(f"got the class {mode.__qualname__} itself")

    def decorator(cls: _RT) -> _RT:
        if not isinstance(mode, RoleMode):
            raise TypeError(f"got {mode!r}")
        setattr(cls, "_role_mode_info", {"mode": mode})  # noqa: B010
        return cls

    return decorator


def use(obj: Any) -> Any:
    """Exercise the decorator both ways so the probe is not dead code."""
    return role_mode(obj)  # type: ignore[arg-type]
