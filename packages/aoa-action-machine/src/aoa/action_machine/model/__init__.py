# packages/aoa-action-machine/src/aoa/action_machine/model/__init__.py
"""
ActionMachine core model public API.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This package exports the base model contracts used by actions:
``BaseAction``, ``BaseParams``, ``BaseResult``, ``ParamsStub``, ``ResultStub``,
``BaseSchema``, ``BaseState``, ``JsonSchemaValue``, ``JsonValue``,
``get_json_schema_value_metadata``, ``is_json_schema_value_type``.
Aspect ``box`` typing lives at :class:`aoa.action_machine.runtime.tools_box.ToolsBox` (import from that module).

``JsonSchemaValue`` (with ``JsonValue`` and the graph helpers above) is the supported way to put
**schema-validated JSON** on a single field of ``BaseResult`` or ``BaseParams`` while keeping
co-located scalar and structured Pydantic fields unchanged. Adapters and the interchange graph
read the resulting models through normal Pydantic APIs (``model_dump``, ``model_json_schema``,
``FieldGraphNode`` metadata).
Framework exceptions live in :mod:`aoa.action_machine.exceptions`.
Graph model nodes/inspectors live under :mod:`aoa.action_machine.graph` and are
imported from their leaf modules.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Action implementation
          |
          +--> BaseParams  (input contract)
          +--> BaseState   (mutable execution state)
          +--> BaseResult  (output contract)
          +--> BaseSchema  (typed schema helpers)
          |
          v
       BaseAction (ties contracts together)
          |
          v
    Runtime / adapters consume typed model interfaces
          |
          +--> JsonSchemaValue / get_json_schema_value_metadata  (optional JSON Schema fields + graph metadata)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    A feature imports ``BaseAction`` and base contracts from this package and
    defines strongly typed params/state/result models for one action.

Edge case:
    A model validation or contract misuse raises an exception from
    :mod:`aoa.action_machine.exceptions`.
"""

from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_schema import BaseSchema
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.json_schema_value import (
    JsonSchemaValue,
    JsonValue,
    get_json_schema_value_metadata,
    is_json_schema_value_type,
)
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub

__all__ = [
    "BaseAction",
    "BaseParams",
    "BaseResult",
    "BaseSchema",
    "BaseState",
    "JsonSchemaValue",
    "JsonValue",
    "ParamsStub",
    "ResultStub",
    "get_json_schema_value_metadata",
    "is_json_schema_value_type",
]
