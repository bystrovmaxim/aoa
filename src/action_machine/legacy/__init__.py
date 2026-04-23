# src/action_machine/legacy/__init__.py
"""Legacy graph topology helpers for role-class interchange."""

from __future__ import annotations

import importlib
from typing import Any

# Eager imports on ``action_machine.legacy`` would run before heavy submodules
# and create import cycles with ``BaseResource`` / ``BaseAction``.
# Resolve public symbols lazily (PEP 562).

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "ActionMetaIntent": ("action_machine.intents.meta.action_meta_intent", "ActionMetaIntent"),
    "AspectIntent": ("action_machine.intents.aspects.aspect_intent", "AspectIntent"),
    "AspectIntentInspector": (
        "action_machine.legacy.aspect_intent_inspector",
        "AspectIntentInspector",
    ),
    "hydrate_aspect_row": (
        "action_machine.legacy.aspect_intent_inspector",
        "hydrate_aspect_row",
    ),
    "CheckRolesIntent": ("action_machine.intents.check_roles.check_roles_intent", "CheckRolesIntent"),
    "CheckerIntent": ("action_machine.intents.checkers.checker_intent", "CheckerIntent"),
    "CheckerIntentInspector": (
        "action_machine.legacy.checker_intent_inspector",
        "CheckerIntentInspector",
    ),
    "hydrate_checker_row": (
        "action_machine.legacy.checker_intent_inspector",
        "hydrate_checker_row",
    ),
    "CompensateIntent": ("action_machine.intents.compensate.compensate_intent", "CompensateIntent"),
    "CompensateIntentInspector": (
        "action_machine.legacy.compensate_intent_inspector",
        "CompensateIntentInspector",
    ),
    "hydrate_compensator_row": (
        "action_machine.legacy.compensate_intent_inspector",
        "hydrate_compensator_row",
    ),
    "hydrate_error_handler_row": (
        "action_machine.legacy.on_error_intent_inspector",
        "hydrate_error_handler_row",
    ),
    "Core": ("action_machine.legacy.core", "Core"),
    "ConnectionIntent": (
        "action_machine.intents.connection.connection_intent",
        "ConnectionIntent",
    ),
    "ConnectionIntentInspector": (
        "action_machine.legacy.connection_intent_inspector",
        "ConnectionIntentInspector",
    ),
    "ContextRequiresIntent": (
        "action_machine.intents.context.context_requires_intent",
        "ContextRequiresIntent",
    ),
    "DescribedFieldsIntent": (
        "action_machine.legacy.described_fields",
        "DescribedFieldsIntent",
    ),
    "validate_described_schema": (
        "action_machine.legacy.described_fields",
        "validate_described_schema",
    ),
    "validate_described_schemas_for_action": (
        "action_machine.legacy.described_fields",
        "validate_described_schemas_for_action",
    ),
    "DescribedFieldsIntentInspector": (
        "action_machine.legacy.described_fields.described_fields_intent_inspector",
        "DescribedFieldsIntentInspector",
    ),
    "DependencyIntent": (
        "action_machine.intents.depends.dependency_intent",
        "DependencyIntent",
    ),
    "DependencyIntentInspector": (
        "action_machine.legacy.dependency_intent_inspector",
        "DependencyIntentInspector",
    ),
    "EntityIntent": ("action_machine.intents.entity.entity_intent", "EntityIntent"),
    "entity_info_is_set": ("action_machine.intents.entity.entity_intent", "entity_info_is_set"),
    "EntityIntentInspector": (
        "action_machine.legacy.entity_intent_inspector",
        "EntityIntentInspector",
    ),
    "MetaIntentInspector": (
        "action_machine.legacy.meta_intent_inspector",
        "MetaIntentInspector",
    ),
    "OnErrorIntent": ("action_machine.intents.on_error.on_error_intent", "OnErrorIntent"),
    "OnErrorIntentInspector": (
        "action_machine.legacy.on_error_intent_inspector",
        "OnErrorIntentInspector",
    ),
    "OnIntent": ("action_machine.intents.on.on_intent", "OnIntent"),
    "ResourceMetaIntent": (
        "action_machine.intents.meta.resource_meta_intent",
        "ResourceMetaIntent",
    ),
    "RoleClassInspector": (
        "action_machine.legacy.role_class_inspector",
        "RoleClassInspector",
    ),
    "ROLE_CLASS_GRAPH_ROOTS": (
        "action_machine.legacy.role_graph_roots",
        "ROLE_CLASS_GRAPH_ROOTS",
    ),
    "role_class_topology_anchor": (
        "action_machine.legacy.role_graph_roots",
        "role_class_topology_anchor",
    ),
    "RoleIntentInspector": (
        "action_machine.legacy.role_intent_inspector",
        "RoleIntentInspector",
    ),
    "RoleModeIntent": ("action_machine.intents.role_mode.role_mode_intent", "RoleModeIntent"),
    "RoleModeIntentInspector": (
        "action_machine.legacy.role_mode_intent_inspector",
        "RoleModeIntentInspector",
    ),
    "SensitiveIntentInspector": (
        "action_machine.legacy.sensitive_intent_inspector",
        "SensitiveIntentInspector",
    ),
    "SubscriptionIntentInspector": (
        "action_machine.legacy.subscription_intent_inspector",
        "SubscriptionIntentInspector",
    ),
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        mod_path, attr = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(importlib.import_module(mod_path), attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
