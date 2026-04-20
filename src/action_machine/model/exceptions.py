# src/action_machine/model/exceptions.py
"""
Raises ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module contains all framework-level custom exceptions for ActionMachine.
Each exception maps to a specific failure category and is consumed by specific
runtime components.

- AuthorizationError - role verification failures in runtime authorization checks.
- ValidationFieldError - validation failures (checkers, runtime guards, protocol input).
- HandleError - action/resource execution failures (for example DB/resource layer).
- TransactionError - base category for transaction/connection lifecycle failures.
- ConnectionAlreadyOpenError - duplicate connection-open attempt.
- ConnectionNotOpenError - operation attempted without an open connection.
- TransactionProhibitedError - prohibited transaction control in nested wrapper scope.
- ConnectionValidationError - provided ``connections`` do not match ``@connection``.
- RollupNotSupportedError - resource/dependency does not support rollup mode.
- LogTemplateError - invalid logging template expression or variable usage.
- CyclicDependencyError - dependency graph cycle detected during coordinator build.
- OnErrorHandlerError - ``@on_error`` handler failed while processing aspect error.
- ContextAccessError - undeclared context key access outside ``@context_requires``.
- NamingSuffixError - naming invariant failure for required suffixes.
- NamingPrefixError - naming invariant failure for required prefixes.

═══════════════════════════════════════════════════════════════════════════════
ERROR HANDLING PHILOSOPHY
═══════════════════════════════════════════════════════════════════════════════

ActionMachine does not silently suppress framework errors. Failures are raised
with explicit messages that describe cause and context. This enables fail-fast
diagnostics at startup/runtime boundaries instead of delayed log-only discovery.

═══════════════════════════════════════════════════════════════════════════════
TRANSACTION EXCEPTION HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

    TransactionError (base)
        ├── ConnectionAlreadyOpenError
        ├── ConnectionNotOpenError
        ├── TransactionProhibitedError
        ├── ConnectionValidationError
        └── RollupNotSupportedError

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Runtime component raises low-level failure
                     |
                     v
    ActionMachine custom exception (typed category)
                     |
                     v
    Machine/adapter boundary decides propagation/wrapping
                     |
                     v
    Caller/tests receive stable, typed error contract

``ValidationFieldError`` may carry optional ``details`` (structured dict) for
callers that need machine-readable context; ``str(exc)`` remains the human
``message`` only.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Components raise domain-appropriate exception types, and tests assert by
    class (and optionally message fragments) for deterministic behavior.

Edge case:
    ``@on_error`` handler itself fails; runtime wraps it in
    ``OnErrorHandlerError`` while preserving original exception via ``__cause__``.

Edge case:
    An adapter maps transport validation (for example Pydantic) into
    ``ValidationFieldError`` with ``details`` so agents receive field-level
    errors without re-parsing exception text.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Central typed failure taxonomy for ActionMachine.
CONTRACT: Raise explicit, category-specific exceptions across subsystems.
INVARIANTS: Transaction errors inherit TransactionError; naming errors use TypeError.
FLOW: subsystem failure -> typed exception -> runtime propagation/wrapping.
FAILURES: Misconfiguration, validation (optional structured details), authorization, orchestration.
EXTENSION POINTS: Add new exception subclasses with narrow semantic scope.
AI-CORE-END
"""

from typing import Any


class AuthorizationError(Exception):
    """
    Authorization failure (insufficient role permissions).
    """

    pass


class ActionResultTypeError(TypeError):
    """
    Summary or ``@on_error`` returned a value that is not the action's declared ``R``.

    Raised when runtime type does not match ``BaseAction[P, R]`` (e.g. wrong
    ``BaseResult`` subclass). Carries expected/actual types for adapters and tests.
    """

    def __init__(
        self,
        message: str,
        *,
        expected_type: type,
        actual_type: type,
    ) -> None:
        super().__init__(message)
        self.expected_type: type = expected_type
        self.actual_type: type = actual_type


class MissingSummaryAspectError(TypeError):
    """
    Action declares a custom ``Result`` subtype but has no ``@summary_aspect``.

    Empty ``BaseResult()`` is only synthesized when ``R`` is exactly ``BaseResult``.
    """

    pass


class ActionResultDeclarationError(TypeError):
    """
    ``BaseAction[P, R]`` result type is missing, not a ``BaseResult`` subclass,
    or not resolvable from generics / forward references.
    """

    pass


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


class HandleError(Exception):
    """
    Error while executing core action/resource logic.
    """

    pass


class TransactionError(Exception):
    """
    Base exception for transaction and connection lifecycle failures.
    """

    pass


class ConnectionAlreadyOpenError(TransactionError):
    """Connection is already open (duplicate open attempt)."""

    pass


class ConnectionNotOpenError(TransactionError):
    """Connection is not open for requested operation."""

    pass


class TransactionProhibitedError(TransactionError):
    """
    Transaction control was attempted in a prohibited nested scope.
    """

    pass


class ConnectionValidationError(TransactionError):
    """
    Provided ``connections`` payload does not match ``@connection`` declaration.
    """

    pass


class RollupNotSupportedError(TransactionError):
    """
    Rollup mode is requested for a manager that cannot provide it.
    """

    pass


class LogTemplateError(Exception):
    """
    Logging template syntax/semantic error.
    """

    pass


class CyclicDependencyError(Exception):
    """
    Dependency graph became cyclic during edge insertion.
    """

    pass


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


class ContextAccessError(Exception):
    """
    Access attempt to a context field not declared in ``@context_requires``.
    """

    def __init__(self, key: str, allowed_keys: frozenset[str]) -> None:
        """Initialize context access violation details."""
        self.key: str = key
        self.allowed_keys: frozenset[str] = allowed_keys
        super().__init__(
            f"Access to context field '{key}' is forbidden. "
            f"Allowed fields: {sorted(allowed_keys)}. "
            f"Add '{key}' to the aspect's @context_requires decorator."
        )


class NamingSuffixError(TypeError):
    """
    ActionMachine naming invariant violation (required suffix).
    """

    pass


class NamingPrefixError(TypeError):
    """
    ActionMachine naming invariant violation (required prefix).
    """

    pass


__all__ = [
    "ActionResultDeclarationError",
    "ActionResultTypeError",
    "AuthorizationError",
    "ConnectionAlreadyOpenError",
    "ConnectionNotOpenError",
    "ConnectionValidationError",
    "ContextAccessError",
    "CyclicDependencyError",
    "HandleError",
    "LogTemplateError",
    "MissingSummaryAspectError",
    "NamingPrefixError",
    "NamingSuffixError",
    "OnErrorHandlerError",
    "RollupNotSupportedError",
    "TransactionError",
    "TransactionProhibitedError",
    "ValidationFieldError",
]
