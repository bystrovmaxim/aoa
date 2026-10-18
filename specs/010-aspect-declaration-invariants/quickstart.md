# Quickstart — how to verify this feature by hand

**Feature**: `specs/010-aspect-declaration-invariants` | **Date**: 2026-10-18

Five checks, each runnable on its own. They correspond to the spec's success criteria; none of them depends on the others, and each must fail on the tree **before** the change — that is what makes it a check rather than a demonstration.

Prerequisites: the repository's environment (`uv` present, `uv sync --extra dev` already done, `.venv` usable), repository root as working directory.

## 1. A renamed declaration is refused where it is written (US1, SC-001, SC-002)

```bash
.venv/bin/python - <<'PY'
from aoa.action_machine.intents.aspects import summary_aspect

@summary_aspect("S")
async def renamed_summary(self, p, state, box, connections):
    return None
PY
```

**Expected after the change**: `AspectSignatureError` naming `(self, params, state, box, connections)` and the written order.
**Expected before**: nothing — the function is created (`renamed_summary` exists).

## 2. An untyped declaration is refused, and a mistyped one fails at assembly (US2, SC-001)

```bash
.venv/bin/python - <<'PY'
from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, ParamsStub, ResultStub
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode

class DemoDomain(BaseDomain):
    name = "demo"
    description = "Demo"

@meta(description="untyped summary", domain=DemoDomain)
@check_roles(GuestRole)
class UntypedAction(BaseAction[ParamsStub, ResultStub]):
    @summary_aspect("No annotations at all")
    async def untyped_summary(self, params, state, box, connections):
        return ResultStub()
PY
```

**Expected after**: `AspectSignatureError` about the missing annotation, at class creation (the class never reaches `ActionGraphNode`).
Then repeat with correct annotations but `box: str`, build `ActionGraphNode(ThatAction)`, and expect `AspectSignatureError` naming `box` — from assembly, not from the first call.

## 3. Two summaries are reported as two summaries (US3, SC-006)

```bash
.venv/bin/python - <<'PY'
from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, ParamsStub, ResultStub
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode

class TwoDomain(BaseDomain):
    name = "two"
    description = "Two"

@meta(description="two summaries", domain=TwoDomain)
@check_roles(GuestRole)
class TwoSummariesAction(BaseAction[ParamsStub, ResultStub]):
    @summary_aspect("First")
    async def first_summary(self, params: ParamsStub, state, box, connections) -> ResultStub:
        return ResultStub()

    @summary_aspect("Second")
    async def second_summary(self, params: ParamsStub, state, box, connections) -> ResultStub:
        return ResultStub()

ActionGraphNode(TwoSummariesAction)
PY
```

**Expected after**: `DuplicateSummaryAspectError` naming both methods.
**Expected before**: `InvalidGraphError: ... references missing target_node_id '...:second_summary'`.
The check also asserts that the string `missing target_node_id` does not appear.

## 4. A summary's answer is the operation's `Result` (US4, SC-007)

Two halves, both required by the clarification:

```bash
# (a) the annotation is refused at assembly
#     annotate the summary `-> Any` and build ActionGraphNode(...)
#     expect AspectSignatureError about the return

# (b) the instance is refused at run time
.venv/bin/python - <<'PY'
import asyncio
from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, ParamsStub, ResultStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class JunkDomain(BaseDomain):
    name = "junk"
    description = "Junk"

@meta(description="summary returns a dict", domain=JunkDomain)
@check_roles(GuestRole)
class JunkAction(BaseAction[ParamsStub, ResultStub]):
    @summary_aspect("Return a dict")
    async def junk_summary(self, params: ParamsStub, state, box, connections) -> ResultStub:
        return {"not": "a result"}

print(asyncio.run(ActionProductMachine().run(Context(), JunkAction(), ParamsStub())))
PY
```

**Expected after**: `ActionResultTypeError` naming the operation, `ResultStub` and `dict`.
**Expected before**: the probe prints `{'not': 'a result'}` — this is the measured defect the feature exists for.

## 5. The corpus complies and the repository is green (US5, SC-003, SC-004)

```bash
# every example script, one process per file; a refusal is an import-time failure
for f in $(find examples -name '*.py' | sort); do .venv/bin/python "$f" >/dev/null || echo "FAILED: $f"; done

# the closing run, with the two accepted remarks left in the log
bash scripts/run_checks_with_log.sh
tail -40 archive/logs/check-all.txt
```

**Expected**: no `FAILED:` line; the check run ends green; `archive/logs/check-all.txt` mentions only the two accepted remarks (Vite chunk size, LangGraph's pending-deprecation warning).

## 6. Invariance (SC-005)

Run any example that was **already** compliant before the change (for example `examples/step_03_authorization_and_roles/06_the_declaration.py`) and compare its output with `git stash`ed `main`: identical, and the check run's event/log assertions in the suite stay green.

## What not to use as evidence

- A screenshot of a traceback, or a paraphrase of a message: paste the message.
- A suite run whose fixtures were rewritten to comply: it proves the checks accept correct code, not that they refuse incorrect code. The refusal probes above are the proof.
