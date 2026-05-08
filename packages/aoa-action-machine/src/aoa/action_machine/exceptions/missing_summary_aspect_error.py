# packages/aoa-action-machine/src/aoa/action_machine/exceptions/missing_summary_aspect_error.py
"""MissingSummaryAspectError."""


class MissingSummaryAspectError(TypeError):
    """Raised when a summary pipeline runs without a declared ``@summary_aspect`` interchange."""
