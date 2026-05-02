# src/action_machine/intents/action_schema/action_schema_intent_resolver.py
"""ActionSchemaIntentResolver — resolves params/result schema intent for actions."""

from __future__ import annotations

from typing import Literal, get_args, get_origin

from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.runtime.binding.action_generic_params import _resolve_generic_arg


class ActionSchemaIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Resolve params/result schema intent declared by an action class generic binding.
    CONTRACT: Returns concrete ``BaseParams`` / ``BaseResult`` subclasses when they can be resolved from ``BaseAction[P, R]``; otherwise returns ``None``.
    AI-CORE-END
    """

    @staticmethod
    def resolve_params_type(action_cls: type) -> type[BaseParams] | None:
        """Resolve the ``BaseAction[P, R]`` params type."""
        params_type = ActionSchemaIntentResolver._resolve_schema_type(action_cls, 0)
        if isinstance(params_type, type) and issubclass(params_type, BaseParams):
            return params_type
        return None

    @staticmethod
    def resolve_result_type(action_cls: type) -> type[BaseResult] | None:
        """Resolve the ``BaseAction[P, R]`` result type."""
        result_type = ActionSchemaIntentResolver._resolve_schema_type(action_cls, 1)
        if isinstance(result_type, type) and issubclass(result_type, BaseResult):
            return result_type
        return None

    @staticmethod
    def _resolve_schema_type(
        action_cls: type,
        type_arg_index: Literal[0, 1],
    ) -> type | None:
        for klass in action_cls.__mro__:
            for base in getattr(klass, "__orig_bases__", ()):
                if get_origin(base) is BaseAction:
                    args = get_args(base)
                    if len(args) <= type_arg_index:
                        return None
                    resolved_type = _resolve_generic_arg(args[type_arg_index], action_cls)
                    return resolved_type if isinstance(resolved_type, type) else None
        return None
