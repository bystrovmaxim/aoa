# packages/aoa-action-machine/src/aoa/action_machine/exceptions/on_error_handler_error.py
"""OnErrorHandlerError."""


class OnErrorHandlerError(Exception):
    """
    Error raised inside an ``@on_error`` handler.

    Preserves handler name and original aspect error context.
    """

    def __init__(
        self,
        message: str,
        handler_name: str,
        original_error: Exception,
    ) -> None:
        """Initialize wrapper for failed ``@on_error`` handler execution."""
        super().__init__(message)
        self.handler_name: str = handler_name
        self.original_error: Exception = original_error
