# packages/aoa-action-machine/src/aoa/action_machine/naming/suffix.py
"""
NamingSuffix — require a primitive's kind at the end of its class name.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A name identifies its primitive family. Rejected declarations receive the same
error shape, including the responsible base and a proposed corrected name.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Base __init_subclass__ -> require_suffix -> accept or NamingSuffixError
"""

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError


def require_suffix(cls: type, base_name: str, suffix: str) -> None:
    """
    Require a class name to end with its primitive family's suffix.

    AI-CORE-BEGIN
    ROLE: Shared naming contract for primitive subclass declarations.
    CONTRACT: Raise NamingSuffixError with class, base, suffix and suggested name when the suffix is missing.
    INVARIANTS: Matching is case-sensitive and checks the end of the name; classes are never renamed implicitly.
    AI-CORE-END
    """
    if not cls.__name__.endswith(suffix):
        raise NamingSuffixError(
            f"Class '{cls.__name__}' inherits {base_name} but lacks the '{suffix}' suffix. "
            f"Rename to '{cls.__name__}{suffix}'."
        )
