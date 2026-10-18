# packages/aoa-action-machine/src/aoa/action_machine/exceptions/duplicate_summary_aspect_error.py
"""
DuplicateSummaryAspectError — an operation declares more than one summary aspect.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An operation answers once: exactly one ``@summary_aspect`` assembles and returns the
``Result``. A second one means two exit points, and the machine cannot say which one
decided — so the declaration is refused where the capability is assembled, before any
call is served, and the message names both methods.

Without this error the duplicate surfaces as a graph failure naming an edge whose
target node does not exist — a message about a node the developer never wrote, in place
of the sentence that says what actually went wrong.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect ──┐
                      ├──▶ SummaryAspectIntentResolver ──▶ DuplicateSummaryAspectError
    @summary_aspect ──┘         (two own-class declarations)

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: how many summaries one operation declares in its own namespace.

OUT: how many summaries it declares in total through its bases — a declaration is never
inherited, so a base's summary does not count against the subclass.
"""

from __future__ import annotations


class DuplicateSummaryAspectError(TypeError):
    """
    AI-CORE-BEGIN
    ROLE: Raised when an operation declares more than one summary aspect of its own.
    CONTRACT: Type ``TypeError``, like ``DuplicateAccessDecideError`` — a declaration mistake, not a failure of a run. The message names the operation and both methods, and never mentions a graph node: the duplicate is the defect, not its symptom.
    INVARIANTS: Raised at assembly, before any call is served; an operation with no summary keeps ``MissingSummaryAspectError``, because "none" and "two" are different answers.
    AI-CORE-END
    """

    pass
