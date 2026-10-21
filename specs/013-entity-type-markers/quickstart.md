# Quickstart — proving the six kinds end to end

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

Every command below runs from the repository root with the repository's own environment. The counts and outputs are what the delivered branch must produce; a different answer is a defect, not an environment quirk.

## Prerequisites

```bash
cd /Users/bystrovmaxim/PythonDev/aoa
uv sync --extra dev           # the eight packages, editable
```

`examples/` are not installed as a package; they run from the source tree, as they do today.

## 1. Six markers exist, are abstract, and carry their kind

```bash
uv run python - <<'PY'
from aoa.action_machine.domain import (
    BaseCoreEntity, BaseAssocEntity, BaseDetailEntity,
    BaseSpecEntity, BaseEnumEntity, BaseStateEntity, EntityKind,
)
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model

for marker, kind in [
    (BaseCoreEntity, EntityKind.CORE), (BaseAssocEntity, EntityKind.ASSOC),
    (BaseDetailEntity, EntityKind.DETAIL), (BaseSpecEntity, EntityKind.SPEC),
    (BaseEnumEntity, EntityKind.ENUM), (BaseStateEntity, EntityKind.STATE),
]:
    print(marker.__name__, kind.word, kind.suffix, excluded_from_graph_model(marker))
    try:
        marker()
    except TypeError as exc:
        print("  refused:", exc)
PY
```

Expected: six lines, one per marker, each ending `True`, each followed by `refused: …` — no marker constructs. A marker missing from the import is a facade defect; a marker that constructs is a missing guard.

## 2. The declaration rules refuse where the class is written

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_markers.py -v
```

Expected: one test per row of the refusal table in [the declaration contract](./contracts/entity-kind-declaration-contract.md) — no marker, two markers, a marker as a target, a missing suffix, a foreign suffix — all raising at import of the module that declares them, plus the accepted cases: an intermediate abstract descendant, one marker with an ordinary mixin, a class inheriting `BaseEntity` without `@entity`.

Adversarial proof (per `AGENTS.md`): comment out one refusal, confirm exactly its test fails and no other, restore.

## 3. The kind reaches the graph row and survives the store

```bash
uv run python - <<'PY'
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ProbeDomain(BaseDomain):
    """Hold the probe declarations."""

    name = "probe"
    description = "A probe domain"


@entity(description="Probe order", domain=ProbeDomain)
class ProbeOrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")


ProbeOrderCoreEntity.model_rebuild()
machine = ActionProductMachine(loggers=[])
node = next(n for n in machine.graph_coordinator.get_all_nodes() if n.label == "ProbeOrderCoreEntity")
print(node.to_dict()["properties"])
PY
```

Expected: `{'description': 'Probe order', 'entity_kind': 'core'}` — measured on the branch base as `{'description': 'Probe order'}`, so the added key is the only difference. The graph's JSON schema validates the row:

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_graph.py -v
uv run pytest packages/aoa-maxitor/tests -q
```

Expected: the schema test rejects a row with no `entity_kind`; the store round trip returns the kind in the node payload.

## 4. No class inherits the base directly any more

```bash
uv run python specs/013-entity-type-markers/evidence/scan_entity_classes.py
```

Expected, on the delivered branch:

```
classes directly on BaseEntity: 6 (the six markers)
classes on a marker: 539
  with a kind suffix: 539
  without: 0
old names still present in packages/ or examples/: 0
```

Before the change the same scan reports `476` classes directly on the base and `0` with a kind suffix; the two runs are the before/after of the migration.

## 5. The migration changed names only

```bash
uv run python specs/013-entity-type-markers/evidence/compare_baselines.py \
    specs/013-entity-type-markers/evidence/baseline.before.json \
    specs/013-entity-type-markers/evidence/baseline.after.json
```

Expected: `476 classes compared, 0 with a changed field/relation/lifecycle set, 0 missing, 0 added.` The comparison is broken on purpose once — drop a field from one class in a scratch copy — to see it report that class and no other.

## 6. The demo, the examples and every package still work

```bash
uv run pytest packages/aoa-action-machine/tests -q
uv run pytest packages/aoa-demo/tests -q
uv run pytest packages/aoa-maxitor/tests -q
uv run pytest packages/aoa-ocel/tests packages/aoa-fastapi-adapter/tests \
                packages/aoa-mcp-adapter/tests packages/aoa-langgraph/tests \
                packages/aoa-otel/tests -q

for f in examples/step_21_relations/*.py examples/step_22_lifecycle/*.py \
         examples/step_28_entity_kinds/*.py; do
  uv run python "$f" > /dev/null || echo "FAILED: $f"
done
```

Expected: no failures, no `FAILED:` line. The notebooks for those scripts were re-executed in the same phase and show the same output.

## 7. The new example teaches all six kinds and all three refusals

```bash
uv run python examples/step_28_entity_kinds/01_entity_kinds.py
```

Expected: one section per kind (what the instance represents, the class, the suffix, the wire word), then one section per refusal — the error type, the message, and the line that caused it — then the accepted shapes: the intermediate abstract descendant and the marker-plus-mixin class. The notebook beside it walks the same order cell by cell.

## 8. The closing check run is green

```bash
bash scripts/run_checks_with_log.sh
```

Expected: exit 0. Two remarks are accepted and are not to be acted on: the Vite chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning`. Anything else in the log is a failure of this change.

## 9. The docs say what the code does

Open the reference page and the tutorial, and check that each of the six kinds names what an instance represents, its suffix and its wire word, and that each of the three refusals is shown with its error type. The pages written here are reported in both languages, each with its `*.ru_draft.md` beside it.
