# src/action_machine/legacy/__init__.py
"""Legacy graph topology helpers for role-class interchange."""

from action_machine.legacy.aspect_intent import AspectIntent
from action_machine.legacy.aspect_intent_inspector import (
    AspectIntentInspector,
    hydrate_aspect_row,
)
from action_machine.legacy.check_roles_intent import CheckRolesIntent
from action_machine.legacy.checker_intent import CheckerIntent
from action_machine.legacy.checker_intent_inspector import (
    CheckerIntentInspector,
    hydrate_checker_row,
)
from action_machine.legacy.compensate_intent import CompensateIntent
from action_machine.legacy.compensate_intent_inspector import (
    CompensateIntentInspector,
    hydrate_compensator_row,
)
from action_machine.legacy.context_requires_intent import ContextRequiresIntent
from action_machine.legacy.described_fields import (
    DescribedFieldsIntent,
    validate_described_schema,
    validate_described_schemas_for_action,
)
from action_machine.legacy.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.legacy.entity_intent import EntityIntent, entity_info_is_set
from action_machine.legacy.entity_intent_inspector import EntityIntentInspector
from action_machine.legacy.role_class_inspector import RoleClassInspector
from action_machine.legacy.role_graph_roots import (
    ROLE_CLASS_GRAPH_ROOTS,
    role_class_topology_anchor,
)
from action_machine.legacy.role_intent_inspector import RoleIntentInspector
from action_machine.legacy.role_mode_intent_inspector import RoleModeIntentInspector

__all__ = [
    "AspectIntent",
    "AspectIntentInspector",
    "CheckRolesIntent",
    "CheckerIntent",
    "CheckerIntentInspector",
    "CompensateIntent",
    "CompensateIntentInspector",
    "ContextRequiresIntent",
    "DescribedFieldsIntent",
    "DescribedFieldsIntentInspector",
    "EntityIntent",
    "EntityIntentInspector",
    "ROLE_CLASS_GRAPH_ROOTS",
    "RoleClassInspector",
    "RoleIntentInspector",
    "RoleModeIntentInspector",
    "hydrate_aspect_row",
    "hydrate_checker_row",
    "hydrate_compensator_row",
    "role_class_topology_anchor",
    "entity_info_is_set",
    "validate_described_schema",
    "validate_described_schemas_for_action",
]
