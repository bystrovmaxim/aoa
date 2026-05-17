# packages/aoa-action-machine/src/aoa/action_machine/intents/depends/use_case.py
"""
UML Use Case relationship labels for ``@depends(..., mode=...)``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide stable string constants and a single ``VALID_USE_CASE_MODES`` frozenset
used by decorator validation (PR-2+) and graph/runtime metadata.
"""

from __future__ import annotations

from typing import Final

_USE_CASE_INCLUDE: Final[str] = "include"
_USE_CASE_EXTEND: Final[str] = "extend"

VALID_USE_CASE_MODES: Final[frozenset[str]] = frozenset({_USE_CASE_INCLUDE, _USE_CASE_EXTEND})


class UseCase:
    """
    Stereotype strings for action-to-action ``@depends`` edges (UML Use Case diagram).

    Values are immutable ``Final[str]`` aliases; ``VALID_USE_CASE_MODES`` is the
    single source of truth for allowed strings in validation.
    """

    include: Final[str] = _USE_CASE_INCLUDE
    extend: Final[str] = _USE_CASE_EXTEND
