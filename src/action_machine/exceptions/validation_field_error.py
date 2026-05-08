# src/action_machine/exceptions/validation_field_error.py
"""ValidationFieldError."""

from typing import Any


class ValidationFieldError(Exception):
    """
    Validation error for aspect result fields, protocol inputs, and shape guards.

    Raised by result checkers, runtime guards, and adapters (for example MCP tool
    input validation mapped from Pydantic). Optional ``details`` carries
    structured data for machine-facing consumers without changing ``str(exc)``.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Human-readable summary; also ``str(exc)`` for logging and
                simple HTTP/MCP ``message`` fields.
            field: Optional single field name for legacy checker context.
            details: Optional structured payload (for example Pydantic
                ``errors()`` list under key ``"errors"``). Omitted or ``None``
                yields ``self.details == {}``.
        """
        self.message: str = message
        self.field: str | None = field
        self.details: dict[str, Any] = details if details is not None else {}
        super().__init__(message)
