# src/action_machine/adapters/base_route_record.py
"""
BaseRouteRecord — abstract frozen dataclass for adapter route configuration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the shared contract for adapter route records. ``BaseRouteRecord`` holds
configuration common to all protocols and enforces mapping invariants.
Protocol-specific fields are added by concrete subclasses.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

1. Concrete adapter creates a subclass of ``BaseRouteRecord`` (e.g.,
   ``FastApiRouteRecord``) with protocol-specific fields.
2. During record creation, ``__post_init__`` automatically extracts
   ``params_type`` and ``result_type`` from the action's generic parameters
   via ``extract_action_types``.
3. Mapping invariants are validated; if a mapper is required but missing,
   ``ValueError`` is raised.
4. The adapter uses ``effective_request_model`` / ``effective_response_model``
   and associated mappers to translate between protocol payloads and action
   types.

Inheritance sketch::

    BaseRouteRecord (frozen, abstract)
        ├── FastApiRouteRecord(method, path, tags, ...)
        ├── McpRouteRecord(tool_name, description, ...)
        └── GRPCRouteRecord(service_name, method_name, ...)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``BaseRouteRecord`` cannot be instantiated directly (only subclasses).
- ``action_class`` must be a subclass of ``BaseAction``.
- ``params_type`` and ``result_type`` are extracted from action generics.
- If ``request_model`` differs from ``params_type``, ``params_mapper`` is required.
- If ``response_model`` differs from ``result_type``, ``response_mapper`` is required.
- Extracted types are cached on the frozen instance via ``object.__setattr__``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Minimal FastAPI route record
    @dataclass(frozen=True)
    class FastApiRouteRecord(BaseRouteRecord):
        method: str = "POST"
        path: str = "/"

    record = FastApiRouteRecord(action_class=CreateOrderAction, path="/orders")
    # params_type and result_type are automatically extracted

    # With mapper (models differ)
    record = FastApiRouteRecord(
        action_class=CreateOrderAction,
        request_model=CreateOrderRequest,
        params_mapper=map_request_to_params,
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` on direct instantiation, invalid ``action_class``, or extraction
  failure.
- ``ValueError`` when a required mapper is missing.
- Forward references in action generics are resolved using the module where the
  action class is defined (via ``ForwardRef._evaluate``; public
  ``typing.evaluate_forward_ref`` when the minimum Python is 3.14+).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract base for protocol route records.
CONTRACT: Subclasses add protocol fields; action generics provide params/result types.
INVARIANTS: Direct instantiation forbidden; mappers required when models differ.
FLOW: Subclass instantiation -> type extraction -> invariant validation -> adapter usage.
FAILURES: TypeError/ValueError on contract violations.
EXTENSION POINTS: New protocols subclass BaseRouteRecord and add custom fields.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from action_machine.core import action_generic_params as _action_generic_params
from action_machine.core.base_action import BaseAction

extract_action_params_result_types = _action_generic_params.extract_action_params_result_types
# Re-exported for adapter edge tests (forward-ref resolution helpers).
_resolve_forward_ref = _action_generic_params._resolve_forward_ref
_resolve_generic_arg = _action_generic_params._resolve_generic_arg


def extract_action_types(action_class: type) -> tuple[type, type]:
    """
    Extract P (params) and R (result) types from BaseAction[P, R].

    Walks ``__orig_bases__`` of the action class MRO to locate the generic
    instantiation of ``BaseAction``. Supports forward references (strings) for
    nested Params/Result classes.

    Raises:
        TypeError: if extraction fails.
    """
    p_type, r_type = extract_action_params_result_types(action_class)
    if p_type is None or r_type is None:
        raise TypeError(
            f"Failed to extract generic parameters P and R from {action_class.__name__}. "
            f"Action must be declared as BaseAction[Params, Result]."
        )
    return p_type, r_type


# ═════════════════════════════════════════════════════════════════════════════
# BaseRouteRecord
# ═════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BaseRouteRecord:
    """
    Abstract frozen dataclass for a single adapter route configuration.

    Stores fields common to all protocols. Protocol-specific fields are added
    by concrete subclasses. Direct instantiation is forbidden.

    Cached attributes:
        _cached_params_type: extracted P from BaseAction[P, R]
        _cached_result_type: extracted R from BaseAction[P, R]
    """

    action_class: type[BaseAction[Any, Any]]
    request_model: type | None = None
    response_model: type | None = None
    params_mapper: Callable[..., Any] | None = None
    response_mapper: Callable[..., Any] | None = None
    _cached_params_type: type = field(init=False, repr=False)
    _cached_result_type: type = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate invariants and cache extracted types."""
        if self.__class__ is BaseRouteRecord:
            raise TypeError(
                "BaseRouteRecord cannot be instantiated directly. "
                "Create a concrete subclass with protocol-specific fields."
            )

        if not isinstance(self.action_class, type) or not issubclass(self.action_class, BaseAction):
            raise TypeError(
                f"action_class must be a subclass of BaseAction, got {self.action_class!r}."
            )

        p_type, r_type = extract_action_types(self.action_class)
        object.__setattr__(self, "_cached_params_type", p_type)
        object.__setattr__(self, "_cached_result_type", r_type)

        if (
            self.request_model is not None
            and self.request_model is not p_type
            and self.params_mapper is None
        ):
            raise ValueError(
                f"request_model ({self.request_model.__name__}) differs from "
                f"params_type ({p_type.__name__}); params_mapper is required."
            )

        if (
            self.response_model is not None
            and self.response_model is not r_type
            and self.response_mapper is None
        ):
            raise ValueError(
                f"response_model ({self.response_model.__name__}) differs from "
                f"result_type ({r_type.__name__}); response_mapper is required."
            )

    @property
    def params_type(self) -> type:
        """Action params type (P from BaseAction[P, R])."""
        return self._cached_params_type

    @property
    def result_type(self) -> type:
        """Action result type (R from BaseAction[P, R])."""
        return self._cached_result_type

    @property
    def effective_request_model(self) -> type:
        """Effective request model: request_model or params_type."""
        return self.request_model if self.request_model is not None else self.params_type

    @property
    def effective_response_model(self) -> type:
        """Effective response model: response_model or result_type."""
        return self.response_model if self.response_model is not None else self.result_type
