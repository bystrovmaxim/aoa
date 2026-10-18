# packages/aoa-action-machine/src/aoa/action_machine/exceptions/aspect_signature_error.py
"""
AspectSignatureError — a declared aspect's signature is not the one the pipeline calls.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The four declaration decorators — ``@summary_aspect``, ``@regular_aspect``,
``@on_error`` and ``@compensate`` — mark methods the machine calls itself. What a
declaration receives is therefore part of the contract, not the developer's private
business: a renamed or reordered parameter still runs, because Python binds by
position, and it receives something other than it says.

One rule, two moments: the shape that needs no name resolution is refused while the
class body executes, and the types that need the operation's own ``Params`` and
``Result`` are refused when the capability is assembled. This error is raised at both,
and its message says which one it was.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect(...)            ──▶ shape refused         ──▶ AspectSignatureError
    (class body executes)

    ActionGraphNode(...)            ──▶ types refused         ──▶ AspectSignatureError
    (the operation's names exist)

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the names and their order, the presence of annotations, the types those
annotations resolve to, and whether the signature can be called positionally.

OUT: what a declaration answers — a summary's returned value is ``ActionResultTypeError``,
and a second summary is ``DuplicateSummaryAspectError``.
"""

from __future__ import annotations

from aoa.action_machine.exceptions.signature_contract_error import SignatureContractError


class AspectSignatureError(SignatureContractError):
    """
    AI-CORE-BEGIN
    ROLE: Raised when an aspect declaration's signature is not the contract the pipeline calls.
    CONTRACT: Subclasses ``SignatureContractError``, so a handler that catches the existing shape error — or ``TypeError`` — keeps catching this one. The message names the declaration, what the pipeline hands over, and, when the refusal happened at assembly, that the class body had already run.
    INVARIANTS: One name for one rule at both moments; the moment is stated in the message, never in the class name.
    AI-CORE-END
    """

    pass
