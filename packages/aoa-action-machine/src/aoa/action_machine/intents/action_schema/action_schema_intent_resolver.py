# packages/aoa-action-machine/src/aoa/action_machine/intents/action_schema/action_schema_intent_resolver.py
"""ActionSchemaIntentResolver — resolves params/result schema intent for actions."""

from __future__ import annotations

import sys
import typing
from typing import Any, ForwardRef, Literal, get_args, get_origin

from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult


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
                    getattr(origin, "__module__", None)
                    in ("action_machine.model.base_action", "aoa.action_machine.model.base_action")
                    and getattr(origin, "__name__", None) == "BaseAction"
                ):
                    args = get_args(base)
                    if len(args) <= type_arg_index:
                        return None
                    resolved_type = ActionSchemaIntentResolver._resolve_type_arg(
                        args[type_arg_index],
                        action_cls,
                    )
                    return resolved_type if isinstance(resolved_type, type) else None
        return None

    @staticmethod
    def _resolve_type_arg(arg: Any, action_cls: type) -> type | None:
        """Resolve one ``BaseAction[P, R]`` argument in the action class namespace."""
        if isinstance(arg, type):
            return arg
        if isinstance(arg, ForwardRef):
            return ActionSchemaIntentResolver._resolve_forward_type(arg, action_cls)
        if isinstance(arg, str):
            return ActionSchemaIntentResolver._resolve_forward_type(ForwardRef(arg), action_cls)
        return None

    @staticmethod
    def _resolve_forward_type(ref: ForwardRef, action_cls: type) -> type | None:
        """Resolve a forward reference using the action module plus the action class name."""
        module = sys.modules.get(action_cls.__module__)
        globalns: dict[str, Any] = vars(module) if module else {}
        localns: dict[str, Any] = {action_cls.__name__: action_cls}

        try:
            evaluate_forward_ref = getattr(typing, "evaluate_forward_ref", None)
            if evaluate_forward_ref is not None:
                resolved = evaluate_forward_ref(
                    ref,
                    globals=globalns,
                    locals=localns,
                    type_params=(),
                )
            else:
                resolved = ref._evaluate(
                    globalns,
                    localns,
                    None,
                    recursive_guard=frozenset(),
                )
        except Exception:
            return None
        return resolved if isinstance(resolved, type) else None
