# specs/016-value-declaration-consistency/evidence/reproduce_defects.py
"""
Print the four defects this feature fixes, measured on the merged baseline.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The specification quotes four reproduced behaviours. This script reproduces
them again, on demand, so the baseline is a measurement rather than a memory:

1. a declared value's nested data is mutable through ``to_reference()``;
2. a ``@field_serializer`` is bypassed, because the reference is read with
   ``getattr``;
3. ``json.dumps(to_reference())`` raises for a standard non-primitive type;
4. the validation schema rejects a code-only reference the runtime accepts.

Every section prints what it observed; the fourth needs ``jsonschema``, which
the repository already depends on.

Run from the repository root::

    uv run python specs/016-value-declaration-consistency/evidence/reproduce_defects.py
"""

from __future__ import annotations

import json
from datetime import date

from pydantic import BaseModel, Field, field_serializer

from aoa.action_machine.domain import BaseEnumEntity


class _LabelsEnumEntity(BaseEnumEntity):
    """Declare a value with nested data, as the issue's first reproduction does."""

    labels: list[str] = Field(description="Labels")

    ITEM = _LabelsEnumEntity(code="item", display_name="Item", labels=["original"])  # noqa: F821


class _DatedEnumEntity(BaseEnumEntity):
    """Declare a dated reference value with a serializer that formats it."""

    since: date = Field(description="Start date")

    ITEM = _DatedEnumEntity(code="item", display_name="Item", since=date(2020, 1, 2))  # noqa: F821

    @field_serializer("since")
    def serialize_since(self, moment: date) -> str:
        """Format the date for consumers."""
        return moment.strftime("%d/%m/%Y")


class _CurrencyEnumEntity(BaseEnumEntity):
    """Declare the one currency the schema case needs."""

    EUR = _CurrencyEnumEntity(code="eur", display_name="Euro")  # noqa: F821


class _Invoice(BaseModel):
    """Reference a declared currency, so its schema is generated."""

    currency: _CurrencyEnumEntity


def first_defect() -> None:
    """Show that a nested container under the exported reference is the shared one."""
    reference = _LabelsEnumEntity.ITEM.to_reference()
    reference["properties"]["labels"].append("changed")
    print("1. nested mutation reaches the declared value:", _LabelsEnumEntity.by_code("item").labels)


def second_defect() -> None:
    """Show that the declared serializer does not reach the reference form."""
    print("2. model_dump_json:", _DatedEnumEntity.ITEM.model_dump_json())
    print("2. expected by the serializer: 02/01/2020")


def third_defect() -> None:
    """Show that the exported reference cannot always be serialized as JSON."""
    try:
        json.dumps(_DatedEnumEntity.ITEM.to_reference())
    except TypeError as error:
        print(f"3. json.dumps(to_reference()): TypeError: {error}")
    else:
        print("3. json.dumps(to_reference()): no error")


def fourth_defect() -> None:
    """Show that the published input schema requires more than the runtime does."""
    payload = {"currency": {"code": "eur"}}
    print("4. runtime accepts a code-only reference:", _Invoice.model_validate(payload).currency is _CurrencyEnumEntity.EUR)
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover - the repository depends on jsonschema
        print("4. jsonschema is not installed; the schema check was skipped")
        return
    schema = _Invoice.model_json_schema(mode="validation")
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(payload)]
    print("4. the validation schema rejects it with:", errors)


def main() -> None:
    """Print all four reproductions in order."""
    first_defect()
    second_defect()
    third_defect()
    fourth_defect()


if __name__ == "__main__":
    main()
