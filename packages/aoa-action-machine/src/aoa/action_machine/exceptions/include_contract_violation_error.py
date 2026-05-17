# packages/aoa-action-machine/src/aoa/action_machine/exceptions/include_contract_violation_error.py
"""
``IncludeContractViolationError`` — include dependency was not executed.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Raised after a successful root action run when the host declared at least one
``UseCase.include`` dependency on another action type, but that type was never
entered via the official execution path (``_run_internal`` / ``box.run``), as
enforced by the runtime checker (PR-4).
"""

from __future__ import annotations


class IncludeContractViolationError(RuntimeError):
    """
    Raised when ``UseCase.include`` contract is violated for a completed root run.

    Attributes:
        missing_include_types: Declared include dependency types that were not
            observed in the run tracker (empty if the message alone carries detail).
    """

    def __init__(
        self,
        message: str,
        *,
        missing_include_types: frozenset[type] | None = None,
    ) -> None:
        super().__init__(message)
        self.missing_include_types: frozenset[type] = (
            missing_include_types if missing_include_types is not None else frozenset()
        )
