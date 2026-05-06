# src/action_machine/intents/action_schema/action_schema_intent_resolver.py
"""ActionSchemaIntentResolver — resolves params/result schema intent for actions."""

from __future__ import annotations

from typing import Literal, get_args, get_origin

from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.runtime.binding.action_generic_params import _resolve_generic_arg


class ActionSchemaIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve params/result schema intent declared by an action class generic binding.
    CONTRACT: Returns concrete ``BaseParams`` / ``BaseResult`` subclasses resolved from ``BaseAction[P, R]``.
    ``resolve_params_type`` may return ``None`` when args resolve to a non-``BaseParams`` type; ``resolve_result_type`` raises :exc:`ValueError` when args are missing or not a ``BaseResult`` subclass.
    AI-CORE-END
    """

    @staticmethod
    def resolve_params_type(action_cls: type) -> type[BaseParams] | None:
        """Resolve the ``BaseAction[P, R]`` params type."""
        params_type = ActionSchemaIntentResolver._resolve_schema_type(action_cls, 0)
        if params_type is None:
            raise ValueError(
                f"Failed to resolve params type for {action_cls.__name__}. "
                "Action must be declared as BaseAction[Params, Result]."
            )
        if isinstance(params_type, type) and issubclass(params_type, BaseParams):
            return params_type
        return None

    @staticmethod
    def resolve_result_type(action_cls: type) -> type[BaseResult]:
        """Resolve the ``BaseAction[P, R]`` result type (``BaseResult`` subclass)."""
        result_type = ActionSchemaIntentResolver._resolve_schema_type(action_cls, 1)
        if result_type is None:
            raise ValueError(
                f"Failed to resolve result type for {action_cls.__name__}. "
                "Action must be declared as BaseAction[Params, Result].",
            )
        if isinstance(result_type, type) and issubclass(result_type, BaseResult):
            return result_type
        raise ValueError(
            f"Declared result type {getattr(result_type, '__name__', result_type)!r} for "
            f"{action_cls.__name__} must be a subclass of BaseResult.",
        )

    @staticmethod
    def _resolve_schema_type(
        action_cls: type,
        type_arg_index: Literal[0, 1],
    ) -> type | None:
        for klass in action_cls.__mro__:
            for base in getattr(klass, "__orig_bases__", ()):
                origin = get_origin(base)
                if (
                    getattr(origin, "__module__", None) == "action_machine.model.base_action"
                    and getattr(origin, "__name__", None) == "BaseAction"
                ):
                    args = get_args(base)
                    if len(args) <= type_arg_index:
                        return None
                    resolved_type = _resolve_generic_arg(args[type_arg_index], action_cls)
                    return resolved_type if isinstance(resolved_type, type) else None
        return None
