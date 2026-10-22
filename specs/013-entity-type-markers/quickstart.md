# Quickstart — proving the six kinds end to end

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

Every command below runs from the repository root with the repository's own environment. The counts and outputs are what the delivered branch must produce; a different answer is a defect, not an environment quirk.

## Prerequisites

```bash
cd /Users/bystrovmaxim/PythonDev/aoa
uv sync --extra dev           # the eight packages, editable
```

`examples/` are not installed as a package; they run from the source tree, as they do today.

## 1. Six kind base classes exist, are abstract, and derive their kind from their own name

```bash
uv run python - <<'PY'
from aoa.action_machine.domain import (
    BaseCoreEntity, BaseAssocEntity, BaseDetailEntity,
    BaseSpecEntity, BaseEnumEntity, BaseStateEntity,
)
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model

for cls in (BaseCoreEntity, BaseAssocEntity, BaseDetailEntity, BaseSpecEntity, BaseEnumEntity, BaseStateEntity):
    word = cls.__name__.removeprefix("Base").removesuffix("Entity").lower()
    print(cls.__name__, word, excluded_from_graph_model(cls))
    try:
        cls()
    except TypeError as exc:
        print("  refused:", exc)
PY
```

Expected: six lines, each with its word and `True`, each followed by `refused: … is the base class of a kind and cannot be instantiated.` A class missing from the import is a facade defect; a class that constructs is a missing rule in the base.

## 2. The rules refuse where the class is written

```bash
uv run pytest packages/aoa-action-machine/tests/action_machine/domain/test_entity_kind.py -v
```

Expected: one test per row of the refusal table in [the declaration contract](./contracts/entity-kind-declaration-contract.md) — direct inheritance of the base, two kind base classes, a missing suffix, a foreign suffix, a status suffix — all raising at class creation, plus the accepted cases: an intermediate abstract descendant, one kind base class with an ordinary mixin, a class carrying a kind and no `@entity`. One test also scans the tree and asserts that exactly six classes inherit the base directly and override the hook.

Adversarial proof (per `AGENTS.md`): comment out one rule, confirm exactly its tests fail and no other, restore.

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

Expected, on the delivered branch (the totals include the helper classes a test declares, so only the shape and the zeros are fixed):

```
Repository scan — entity classes
  kind base classes found                             6  ['BaseAssocEntity', 'BaseCoreEntity', 'BaseDetailEntity', 'BaseEnumEntity', 'BaseSpecEntity', 'BaseStateEntity']
  classes directly on BaseEntity (real)               0
    of them decorated with @entity                    0
    of them without @entity                           0
  classes on a kind base class                        <n>
    of them on BaseStateEntity                        63
  real classes (on the base or on a kind base class)  <n>
    with a kind suffix                                <n>
    without a kind suffix                             0
      CoreEntity / AssocEntity / DetailEntity / SpecEntity / EnumEntity / StateEntity
  old names recorded in the map                       320 distinct (473 entries)
  old names still present                             0 occurrence(s)
```

The six per-kind lines are the split the mapping produced; their sum is the number of classes on a kind base class. The zero that matters is `without a kind suffix`.

Before the change the same scan reports `476` classes directly on the base, `470` of them decorated, `63` on the state base class, `63` with a kind suffix and `476` without — the block recorded verbatim in `specs/013-entity-type-markers/evidence/scan.before.txt`. The two runs are the before and after of the migration.

## 5. The migration changed names only

```bash
uv run python specs/013-entity-type-markers/evidence/compare_baselines.py \
    --before specs/013-entity-type-markers/evidence/baseline.before.json \
    --after specs/013-entity-type-markers/evidence/baseline.after.json \
    --map-only
```

Expected: `473 classes compared (473 names, 476 declarations), 0 with a changed surface, 0 missing, 0 added.` The three extra declarations are class names a module redefines, so the 476 corpus classes collapse to 473 names. The comparison is broken on purpose once — drop a field from one class in a scratch copy — to see it report that class and no other.

## 6. The demo, the examples and every package still work

```bash
uv run pytest packages/aoa-action-machine/tests -q
uv run pytest packages/aoa-demo/tests -q
uv run pytest packages/aoa-maxitor/tests -q
uv run pytest packages/aoa-ocel/tests packages/aoa-fastapi-adapter/tests \
                packages/aoa-mcp-adapter/tests packages/aoa-langgraph/tests \
                packages/aoa-otel/tests -q

for f in examples/step_21_relations/*.py examples/step_22_lifecycle/*.py; do
  uv run python "$f" > /dev/null || echo "FAILED: $f"
done
```

Expected: no failures, no `FAILED:` line. The notebooks for those scripts were re-executed in the same phase and show the same output.

## 7. The new example teaches all six kinds and both rules

```bash
uv run python examples/step_28_entity_kinds/01_entity_kinds.py
```

Expected: one section per kind (what the instance represents, the class, the suffix, the wire word), then one section per refusal — the error type, the message, and the line that caused it — then the accepted shapes: the intermediate abstract descendant and the mixin case. The notebook beside it walks the same order cell by cell.

## 8. The closing check run is green

```bash
bash scripts/run_checks_with_log.sh
```

Expected: exit 0. Two remarks are accepted and are not to be acted on: the Vite chunk-size advisory and LangGraph's `LangChainPendingDeprecationWarning`. Anything else in the log is a failure of this change.

## 9. The docs say what the code does

Open the reference page and the tutorial, and check that each of the six kinds names what an instance represents, its suffix and its wire word, and that each of the rules is shown with its error type. The pages written here are reported in both languages, each with its `*.ru_draft.md` beside it.
