# Quickstart: the eleven proofs this change has to run

**Feature**: `specs/017-explicit-entity-relations` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md) | **Contracts**: [entity-field-declaration](./contracts/entity-field-declaration.md), [relation-field-metadata](./contracts/relation-field-metadata.md), [dictionary-member](./contracts/dictionary-member.md)

Every proof below is runnable from the repository root after `uv sync --extra dev`. Each one names the requirement it proves and the answer it must produce; a proof that prints something else is a failing phase.

## Prerequisites

```bash
uv sync --extra dev
(cd packages/aoa-maxitor/client && npm ci)
```

## 1. A bare entity-typed field is refused

Proves FR-001, FR-002, US1 scenario 1.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields

class ShowcaseCoreEntity(BaseCoreEntity):
    """A showcase."""
    id: str

class PlayerCoreEntity(BaseCoreEntity):
    """A player."""
    id: str = Field(description="Player identifier")
    showcase: ShowcaseCoreEntity = Field(description="Player showcase")

try:
    validate_entity_fields([PlayerCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming `PlayerCoreEntity.showcase`, the resolved `ShowcaseCoreEntity`, and both legal forms.

## 2. The relation form builds an edge

Proves FR-003, US1 scenario 2.

```bash
uv run --extra dev python - <<'PY'
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, Inverse

class ShowcaseCoreEntity(BaseCoreEntity):
    """A showcase."""
    id: str

class PlayerCoreEntity(BaseCoreEntity):
    """A player."""
    showcase: Annotated[AssociationOne[ShowcaseCoreEntity], Inverse(ShowcaseCoreEntity, "players")] = Field(
        description="Player showcase"
    )

print(PlayerCoreEntity.model_fields["showcase"].description)
PY
```

Expected: `Player showcase`. The corresponding graph test asserts the edge and the foreign-key row.

## 3. The embedded-value marker is legal and quiet

Proves FR-004, US1 scenario 3.

```bash
uv run --extra dev python - <<'PY'
from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, NoRelation

class ShowcaseCoreEntity(BaseCoreEntity):
    """A showcase."""
    id: str

class SnapshotCoreEntity(BaseCoreEntity):
    """Keep a showcase as a value."""
    showcase: Annotated[ShowcaseCoreEntity, NoRelation("embedded snapshot")] = Field(
        description="Showcase snapshot stored as a value"
    )

print(SnapshotCoreEntity.model_fields["showcase"].description)
print(NoRelation("embedded snapshot"))
PY
```

Expected: the description, then `NoRelation('embedded snapshot')`; no relation edge in the graph test, and no new member in the payload.

## 4. A collection of an entity is refused

Proves FR-003's collection rule, research D2.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields

class ShowcaseCoreEntity(BaseCoreEntity):
    """A showcase."""
    id: str

class HolderCoreEntity(BaseCoreEntity):
    """Hold a collection."""
    items: list[ShowcaseCoreEntity] = Field(default_factory=list, description="Items")

try:
    validate_entity_fields([HolderCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming `AssociationMany`/`AggregateMany` as the many-container forms.

## 5. A state-typed field names its only form

Proves FR-003's state rule, US1 scenario 6.

```bash
uv run --extra dev python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, BaseStateEntity
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields

class StageStateEntity(BaseStateEntity):
    """A status."""
    code: str = Field(description="Code")

class OrderCoreEntity(BaseCoreEntity):
    """Describe an order."""
    stage: StageStateEntity = Field(description="Stage")

try:
    validate_entity_fields([OrderCoreEntity])
except Exception as error:
    print(type(error).__name__, error)
PY
```

Expected: a refusal naming `Lifecycle[...]` as the only form.

## 6. A mutable member is refused before publication

Proves FR-008–FR-012, US2 scenarios 1–2.

```bash
uv run --extra dev python - <<'PY'
from pydantic import field_validator
from aoa.action_machine.domain import BaseEnumEntity, value

class LabelsEnumEntity(BaseEnumEntity):
    """Declare labels shared by all users of this value."""
    labels: tuple[str, ...]
    ITEM = value(code="item", display_name="Item", labels=("original",))

    @field_validator("labels", mode="after")
    @classmethod
    def replace_with_list(cls, labels: tuple[str, ...]) -> list[str]:
        """Demonstrate a validator that violates the property contract."""
        return list(labels)
PY
```

Expected: the class body fails with the dictionary, the member, the property path and `list`; `by_code("item")` is never reachable.

## 7. A value of the wrong immutable type is refused too

Proves FR-009, US2 scenario 7.

```bash
uv run --extra dev python - <<'PY'
from pydantic import field_validator
from aoa.action_machine.domain import BaseEnumEntity, value

class ShapeEnumEntity(BaseEnumEntity):
    """Declare a tuple property."""
    labels: tuple[str, ...]
    ITEM = value(code="item", display_name="Item", labels=("a",))

    @field_validator("labels", mode="after")
    @classmethod
    def to_string(cls, labels: tuple[str, ...]) -> str:
        """Return a different immutable type."""
        return ",".join(labels)
PY
```

Expected: a refusal naming `tuple[str, ...]` and `str` — not a serializer warning.

## 8. An `Enum` with a mutable value is refused

Proves FR-010, research D8.

```bash
uv run --extra dev python - <<'PY'
from enum import Enum
from aoa.action_machine.domain import BaseEnumEntity, value

class Flags(Enum):
    """Name the flags."""
    X = ["a", "b"]

class WeirdEnumEntity(BaseEnumEntity):
    """Carry an enum property."""
    flags: Flags
    ITEM = value(code="item", display_name="Item", flags=Flags.X)
PY
```

Expected: a refusal at the `flags` property naming `Flags` and `list`.

## 9. The serialization schema is self-contained

Proves FR-015–FR-019, US3.

```bash
uv run --extra dev python - <<'PY'
from enum import Enum
import json
import jsonschema
from aoa.action_machine.domain import BaseEnumEntity, value

class Grade(Enum):
    """Name the supported grades."""
    A = "a"

class RatedEnumEntity(BaseEnumEntity):
    """Describe a value with an enum property."""
    grade: Grade
    ITEM = value(code="item", display_name="Item", grade=Grade.A)

schema = RatedEnumEntity.model_json_schema(mode="serialization")
exported = RatedEnumEntity.ITEM.to_reference()
jsonschema.validate(instance=exported, schema=schema)
print("validated", sorted(schema.get("$defs", {})))
print(json.dumps(schema["properties"]["properties"], sort_keys=True))
PY
```

Expected: `validated ['Grade']`, and a `properties` object that carries `required` and a `$ref` whose definition exists. A disallowed enum value fails the same schema; the input schema still accepts `{"code": "item"}`.

## 10. The relation default contract, row by row

Proves FR-022–FR-026, US4.

```bash
uv run --extra dev python - <<'PY'
from typing import Annotated
from pydantic import Field, ValidationError
from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse

class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str

class RequiredCoreEntity(BaseCoreEntity):
    """Require the relation."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Related target")

class OmittableCoreEntity(BaseCoreEntity):
    """Allow the relation to be absent."""
    target: Annotated[AssociationOne[TargetCoreEntity] | None, NoInverse()] = Field(
        default=None, description="Related target"
    )

print("required field required:", RequiredCoreEntity.model_fields["target"].is_required())
print("omittable omitted:", OmittableCoreEntity().target)
try:
    RequiredCoreEntity()
except ValidationError:
    print("required omitted: refused")
PY
```

Expected: `required field required: True`, `omittable omitted: None`, `required omitted: refused`. The test suite covers all four rows, the factory refusal and the unexecuted factory.

## 11. The card prints labels and keeps the code in the tooltip

Proves FR-037–FR-040, US6.

```bash
(cd packages/aoa-maxitor/client && node scripts/check-erd-dictionary-values.ts)
uv run --extra dev pytest packages/aoa-maxitor/tests -q -k "dictionary"
```

Expected: the check asserts the printed text has no code, the DOT carries `TOOLTIP="code: …"`, and the payload test asserts the enum's field list has no `code`/`display_name` while the graph JSON still carries both.

## The closing run

```bash
bash scripts/run_checks_with_log.sh
```

Expected: no errors, and exactly two remarks — the Vite chunk-size advisory and LangGraph's pending-deprecation warning. The tail of `archive/logs/check-all.txt` is the evidence pasted into the report.

## What a phase must show before it is committed

1. Its proof above runs and prints the expected answer.
2. The affected package's `pytest` is green, and the demo's suite with it.
3. Its defect, reintroduced in isolation, makes the targeted test fail while an unrelated test in the same run passes, and the implementation is restored.
