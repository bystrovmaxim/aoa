# packages/aoa-demo/tests/model/test_result_round_trip.py
"""
Every Result class of the demo reads back from its JSON with the same observable state.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Rule 2 of #399 (issue #409). The demo's actions need a database to run, so each
Result class is built from a sample made from its own published JSON Schema
(validation mode), then written as JSON, read back and compared with
``observable_difference``. The sample takes each object's required properties, the
smallest value a constraint allows and the first branch of ``anyOf`` that is not
``null``; a keyword the sample does not know fails the test, so a new kind of Result
is not skipped silently.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

import pytest

import aoa.demo
from aoa.action_machine.domain import observable_difference
from aoa.action_machine.model import BaseResult

# Keywords that describe a value without constraining the sample.
_DESCRIPTIVE = {"title", "description", "default", "examples", "additionalProperties", "$defs", "deprecated"}


def _subclasses(cls: type) -> set[type]:
    found: set[type] = set()
    for sub in cls.__subclasses__():
        found |= {sub, *_subclasses(sub)}
    return found


def _demo_results() -> list[type[BaseResult]]:
    for module in pkgutil.walk_packages(aoa.demo.__path__, f"{aoa.demo.__name__}."):
        importlib.import_module(module.name)
    found = [cls for cls in _subclasses(BaseResult) if cls.__module__.startswith("aoa.demo.")]
    return sorted(found, key=lambda cls: f"{cls.__module__}.{cls.__qualname__}")


def _sample(schema: dict[str, Any], definitions: dict[str, Any]) -> Any:
    """The smallest value ``schema`` accepts."""
    if "$ref" in schema:
        return _sample(definitions[schema["$ref"].rsplit("/", 1)[-1]], definitions)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        branches = [branch for branch in schema["anyOf"] if branch.get("type") != "null"]
        return _sample(branches[0] if branches else {"type": "null"}, definitions)
    unknown = set(schema) - _DESCRIPTIVE - {
        "type", "properties", "required", "items", "minimum", "exclusiveMinimum", "minLength", "minItems",
    }
    if unknown:
        raise ValueError(f"the sample does not know {sorted(unknown)} in {schema}")
    kind = schema.get("type")
    if kind == "object":
        properties = schema.get("properties", {})
        return {name: _sample(properties[name], definitions) for name in schema.get("required", [])}
    if kind == "array":
        return [_sample(schema.get("items", {}), definitions) for _ in range(max(1, schema.get("minItems", 0)))]
    if kind == "string":
        return "s" * max(1, schema.get("minLength", 0))
    if kind in ("integer", "number"):
        if "exclusiveMinimum" in schema:
            return schema["exclusiveMinimum"] + 1
        return schema.get("minimum", 1)
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    raise ValueError(f"the sample does not know type {kind!r} in {schema}")


RESULTS = _demo_results()


def test_the_demo_has_its_results() -> None:
    """The walk finds the demo's Result classes, so the read-back below is not empty."""
    assert len(RESULTS) >= 58


@pytest.mark.parametrize("result_cls", RESULTS, ids=lambda cls: cls.__qualname__)
def test_a_demo_result_reads_back_with_the_same_observable_state(result_cls: type[BaseResult]) -> None:
    """A sample of the Result, written as JSON and read back, holds what it held."""
    schema = result_cls.model_json_schema(mode="validation")
    value = result_cls.model_validate(_sample(schema, schema.get("$defs", {})))
    back = result_cls.model_validate_json(value.model_dump_json())
    assert observable_difference(value, back) is None
