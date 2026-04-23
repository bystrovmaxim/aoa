# src/action_machine/auth/base_role.py
"""
Abstract base for typed **role marker** classes (frozen declaration, like domains).

Module layout and the full **SystemRole** vs **ApplicationRole** split are
summarized in the package ``__init__`` (**ROLE TYPE HIERARCHY**) and expanded in
``docs/architecture/role-hierarchy.md``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseRole`` is the typed counterpart to string role names: each role is a
**class** carrying stable ``name`` / ``description`` metadata. Implied privileges
follow **Python subclassing** (MRO); ``RoleChecker`` uses ``issubclass`` for grants. The design mirrors ``BaseDomain`` — immutable class-level
declaration, no product instance state.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class OrderViewerRole(BaseRole):
        name = "order_viewer"
        description = "Read-only order visibility."

    @role_mode(RoleMode.ALIVE)
    class OrderManagerRole(OrderViewerRole):
        name = "order_manager"
        description = "Full order control."

    @check_roles(OrderViewerRole)   # action decorator (separate module)
    class GetOrderAction(...):
        ...

"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from action_machine.intents.role_mode.role_mode_intent import RoleModeIntent
from action_machine.exceptions import NamingSuffixError

_REQUIRED_SUFFIX = "Role"


class BaseRole(RoleModeIntent, ABC):
    """
    Abstract base for role marker classes (type-as-capability, like ``BaseDomain``).

    **Contract**
        Supply ``name`` and ``description`` as class attributes.
        Subclass names end with ``Role``. Use ``@role_mode`` for lifecycle mode.
        Use **inheritance** so that broader roles imply narrower ones in ``@check_roles``.

    **Neighbors**
        Referenced from ``@check_roles`` on actions and stored on ``UserInfo.roles``.
    """

    name: ClassVar[str]
    description: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits from BaseRole but its name must "
                f"end with the suffix '{_REQUIRED_SUFFIX}'. "
                f"Rename it to e.g. '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

        _validate_role_class_attr(cls, "name")
        _validate_role_class_attr(cls, "description")


def _validate_role_class_attr(cls: type, attr_name: str) -> None:
    """Ensure ``name`` / ``description`` exist, are ``str``, and are non-empty."""
    if attr_name not in cls.__dict__:
        for base in cls.__mro__[1:]:
            if base is BaseRole:
                continue
            if attr_name in base.__dict__:
                return
        raise ValueError(
            f"Class '{cls.__name__}' inherits from BaseRole but does not define "
            f"the class attribute '{attr_name}'. "
            f"Set e.g. {attr_name} = \"...\" in the class body."
        )

    raw_value = cls.__dict__[attr_name]

    if not isinstance(raw_value, str):
        raise TypeError(
            f"Class attribute '{attr_name}' on '{cls.__name__}' must be str, "
            f"got {type(raw_value).__name__}: {raw_value!r}."
        )

    if not raw_value.strip():
        raise ValueError(
            f"Class attribute '{attr_name}' on '{cls.__name__}' cannot be empty "
            f"or whitespace-only."
        )
