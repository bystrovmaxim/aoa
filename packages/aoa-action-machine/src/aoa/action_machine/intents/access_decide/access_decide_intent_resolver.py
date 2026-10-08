# packages/aoa-action-machine/src/aoa/action_machine/intents/access_decide/access_decide_intent_resolver.py
"""
AccessDecideIntentResolver — find the object check an operation declares, if any.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One place that answers "does this operation declare an object check, and which
callable is it". The lookup reads the operation's **own** namespace, so a
subclass never inherits the decision its parent made; and it refuses to guess
when an operation declares more than one, because two answers to the same
question leave nobody able to say which one decided.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @access_decide ──▶ ``_access_decide_meta`` on the method
                              │
    this resolver ────────────┘  reads the class's own namespace only
        ├── nothing marked        ──▶ None            (the operation has no object check)
        ├── exactly one marked    ──▶ that callable
        └── more than one marked  ──▶ DuplicateAccessDecideError

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the lookup, the "own namespace only" rule, and the duplicate error.

OUT: calling the check and judging its answer — the object step does that.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.duplicate_access_decide_error import DuplicateAccessDecideError
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

_ACCESS_DECIDE_META_ATTR = "_access_decide_meta"


class AccessDecideIntentResolver:
    """
    AI-CORE-BEGIN
        ROLE: Surface the object check an operation declares in its own namespace.
        CONTRACT: :meth:`resolve_check` returns the marked callable, or ``None`` when the operation declares none; more than one raises :exc:`~aoa.action_machine.exceptions.DuplicateAccessDecideError`. :meth:`is_declared` answers the same question without raising.
        INVARIANTS: Reads ``vars(action_cls)`` only, so a declaration is never inherited.
    AI-CORE-END
    """

    @staticmethod
    def resolve_check(action_cls: type[Any]) -> Callable[..., Any] | None:
        """
        Return the operation's own declared object check, or ``None`` when it declares none.

        Raises:
            DuplicateAccessDecideError: the operation declares more than one check.
        """
        declared = AccessDecideIntentResolver._own_declarations(action_cls)
        if not declared:
            return None
        if len(declared) > 1:
            names = ", ".join(sorted(method.__name__ for method in declared))
            raise DuplicateAccessDecideError(
                f"{action_cls.__name__} declares more than one object check ({names}); "
                "an operation answers about its object once."
            )
        return declared[0]

    @staticmethod
    def is_declared(action_cls: type[Any]) -> bool:
        """Return whether the operation declares an object check of its own."""
        return bool(AccessDecideIntentResolver._own_declarations(action_cls))

    @staticmethod
    def _own_declarations(action_cls: type[Any]) -> list[Callable[..., Any]]:
        """Return the marked callables in the operation's own namespace."""
        return TypeIntrospection.collect_own_class_callables(
            action_cls,
            lambda func: getattr(func, _ACCESS_DECIDE_META_ATTR, None) is not None,
        )
