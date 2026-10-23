# Additional code fixes after documentation verification

Comparison base: `origin/main`, merge-base `2e70a30d36471518df9a64f855b30a8c32118ecb`. Evidence includes the committed branch changes and the current working tree. No source behavior was changed during this documentation pass.

## Fix Literal membership after user validation

Priority: high. A dictionary annotated with `Literal["a"]` publishes `"b"` when an after-validator returns it. The completed-value check accepts a supported scalar without checking membership in the literal choices. This allows the member to contradict its declared schema.

The next code change should reject a completed member outside the literal choices. Add a regression test that currently fails, a valid-member neighbor, and nested tuple and optional cases. Keep the diagnostic consistent with other dictionary-property refusals. The exact future diagnostic is not specified here because it does not exist yet.

## Reject None in a non-nullable union

Priority: high. A dictionary property annotated with `str | int` publishes `None` after user validation. The completed-value check accepts null before checking whether the union includes it.

The next code change should accept null only when the annotation includes it. Test both `str | int` and `str | int | None`, including nested tuple properties. This is independent of a relation field's nullable/default rules.

## Reproduce both defects

Save this complete block to a clean file and run it with the repository Python environment:

```python
from typing import Literal
from pydantic import field_validator
from aoa.action_machine.domain import BaseEnumEntity, value

class LiteralProbeEnumEntity(BaseEnumEntity):
    """Reproduce a validator escaping a literal constraint."""
    choice: Literal["a"]
    ITEM = value(code="item", display_name="Item", choice="a")

    @field_validator("choice", mode="after")
    @classmethod
    def replace(cls, original: str) -> str:
        """Return a scalar outside the permitted choices."""
        return "b"

class UnionProbeEnumEntity(BaseEnumEntity):
    """Reproduce a validator escaping a non-null union."""
    choice: str | int
    ITEM = value(code="item", display_name="Item", choice="a")

    @field_validator("choice", mode="after")
    @classmethod
    def replace(cls, original: str | int) -> None:
        """Return null although the annotation excludes it."""
        return None

print("Literal result:", LiteralProbeEnumEntity.ITEM.choice)
print("Non-null union result:", UnionProbeEnumEntity.ITEM.choice)
```

Actual output:

```text
Literal result: b
Non-null union result: None
```

Expected after correction: both invalid class declarations are refused before a member is published. The current output above records defects, not supported forms.

## Documentation and examples delivered

The [dictionary tutorial](../tutorials/step-20-dictionaries.md) and [relation tutorial](../tutorials/step-21-relations.md) now use complete independently runnable examples. [Explicit entity fields](../how-to/explicit-entity-fields.md) explains required values, nullable defaults, embedded entities and exact graph-build refusals. [Dictionary validation and export](../how-to/dictionary-validation-and-export.md) covers completed-value refusals and real serialization schemas. The [invariant reference](../reference/intents-and-invariants.md#relation-descriptions-and-defaults) distinguishes field metadata from relation values.

Before, a relation description occupied the field's default. Now `Field(description="Target")` supplies metadata and the caller supplies the relation value; use `Field(default=None, description="Target")` only with a nullable annotation to allow omission. The classifier now names its dictionary value without repeating the field carrying the marker.

## Verification and its limits

The selected domain, field-declaration, hydration and specialization tests passed: 106 tests. The selected diagram payload and specialization tests passed: 33 tests. The dictionary card renderer check printed `Dictionary card: labels printed, codes carried as tooltips, everything escaped`.

100 scripts and 100 matching notebooks passed. All 23 complete Python blocks in the four rewritten tutorial and how-to pages matched their displayed output. All 245 local links in the new and rewritten pages resolved.

The documentation's complete Python blocks were copied into clean files, run in separate processes, and compared byte-for-byte with the displayed output. Example scripts and Python notebook cells were executed in fresh processes; notebook execution counts and captured outputs were saved. Notebook cells were executed directly as Python, without a Jupyter kernel.

An adversarial run disabled the completed-value check in memory. The mutable-result example then failed with `AssertionError: A mutable dictionary property was published`; the adjacent serialization-schema example still passed. The original function was restored, and source files were not modified by this experiment. A second isolated mutation disabled entity-field declaration validation: the bare-entity example failed with `AssertionError: The invalid declaration was accepted`, while the nullable-relation neighbor passed.

The full repository check runner was not executed during this scoped verification. No claim of a fully green repository gate is made. The two reproductions above remain code defects and need regression tests and fixes before the completed-value check can be described as enforcing every supported annotation.
