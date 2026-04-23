# src/action_machine/exceptions/missing_summary_aspect_error.py
"""MissingSummaryAspectError."""


class MissingSummaryAspectError(TypeError):
    """
    Action declares a custom ``Result`` subtype but has no ``@summary_aspect``.

    Empty ``BaseResult()`` is only synthesized when ``R`` is exactly ``BaseResult``.
    """

    pass
