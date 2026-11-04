# packages/aoa-action-machine/src/aoa/action_machine/system_core/json_schema_check.py
"""
JsonSchemaCheck — a JSON Schema check built once, in the draft it checks values with.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``jsonschema.validate(value, schema)`` does four things on every call: it picks the
validator class for the schema's draft, checks the schema itself in that draft, builds
a validator, and checks the value. The first three depend only on the schema. A
``JsonSchemaValue`` type and an entity projection (``EntitySchemaMarker``) build one
``JsonSchemaCheck`` when they are declared and only check values afterwards, so a
schema its own draft refuses is refused at declaration and a value check checks only
the value.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    JsonSchemaCheck(schema)                       once, at declaration
          |
          +--> validator_for(schema)               the draft named by ``$schema``,
          |                                        the newest one without it
          +--> <draft>.check_schema(schema)        ``SchemaError`` for a refused schema
          +--> <draft>(schema)                     the validator, kept
          |
    check.error_of(value)                         per value
          |
          +--> best_match(validator.iter_errors(value))   the error ``jsonschema.validate``
                                                          would raise, or ``None``
"""

from __future__ import annotations

from typing import Any

from jsonschema.exceptions import ValidationError, best_match
from jsonschema.validators import validator_for


class JsonSchemaCheck:
    """
    AI-CORE-BEGIN
    ROLE: Check values against one JSON Schema, with the schema checked once.
    CONTRACT: Built from a schema: picks the draft as ``jsonschema.validate`` does, checks the schema
              in it (``SchemaError`` on refusal) and keeps the validator; ``error_of`` returns the error
              ``jsonschema.validate`` would raise for a value, or ``None``.
    INVARIANTS: The schema is checked only when the check is built; ``copy``, ``deepcopy`` and
                ``pickle`` rebuild the check from its schema.
    AI-CORE-END
    """

    __slots__ = ("_schema", "_validator")

    def __init__(self, schema: dict[str, Any]) -> None:
        """
        Args:
            schema: The JSON Schema; the draft is the one its ``$schema`` names, the newest without it.

        Raises:
            jsonschema.SchemaError: The schema's draft refuses the schema.
        """
        validator_class = validator_for(schema)
        validator_class.check_schema(schema)
        self._schema = schema
        self._validator = validator_class(schema)

    @property
    def schema(self) -> dict[str, Any]:
        """The schema this check was built from."""
        return self._schema

    def error_of(self, value: Any) -> ValidationError | None:
        """Return the error ``jsonschema.validate`` would raise for ``value``, or ``None`` when it is valid."""
        error: ValidationError | None = best_match(self._validator.iter_errors(value))
        return error

    def __reduce__(self) -> tuple[Any, ...]:
        """Rebuild the check from its schema; the validator itself cannot be pickled."""
        return (JsonSchemaCheck, (self._schema,))
