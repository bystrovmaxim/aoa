# Role declarations and object rules: verification

Verified on 2026-10-25 in the current working tree. The branch is
`feature/issue-248-check-roles-without-grant-guard`; the primary reference is
`origin/main`, and the merge base is
`90dd83e502a0129bd92a8636296efbdb085a9862`.
The branch head inspected at the start was
`c9cd995aa0603b30b9762e0c5363898f410fd972`.

## Evidence boundary

The review covered all six branch commits, the committed changes from the merge
base, the initial working-tree edits, the index and relevant untracked evidence.
The public behavior belongs to [the role-condition removal](https://github.com/bystrovmaxim/aoa/issues/248).
The additionally supplied [dictionary-reference issue](https://github.com/bystrovmaxim/aoa/issues/256)
describes a different change; it was read for context and supplies no evidence
for the role behavior documented here.

The existing edits were retained. This work changes documentation and executable
teaching material; the only additional source edit is the stale `AccessDenied`
docstring. No execution behavior was changed. No commit, push, pull request or
merge was performed by this author, and no staging operation was performed.
The index changed externally during this session and was left as found.

## What is established

| Behavior | Evidence |
| --- | --- |
| Bare, positional, tuple/list role choices and deduplication | Package role-declaration and role-edge tests; declaration and graph scenarios |
| Guest/any alternatives retain sentinel meaning | Role tests and the guest scenario, including an unrelated active auditor |
| A silenced role does not contribute permission | Package role tests and the silenced manager-descendant scenario |
| Guest execution is open without an object rule, but can be refused with one | Guest scenario exercises both query and execution, with exact exception text |
| Caller conditions use declared context | Context tests and the EU-manager scenario; graph scenario checks the required key |
| Conditional refusals use `ACCESS_DECIDE` | Cascade, runtime event, verdict and query/execution tests; amount, reason and execution scenarios |
| Old imports, condition keywords and gate words fail | Removal and verdict tests; migration scenario asserts exact keyword, enum and payload errors |
| Role edges contain no conditions; object rules remain separate | Graph tests and the graph scenario |

A decorator keyword refusal occurs while evaluating the decorator expression.
It is not deferred until execution. `grant` and `Grant` are absent imports,
not deprecated wrappers. The operation has three gate words, and old gate values
fail parsing. A guest declaration still permits an object rule to refuse.

The issue's possible deprecation period and optional action authorization marker
are not implemented. The measured API removes the names immediately and keeps
the existing separate object-rule node. The object rule runs inside execution,
after connection validation; it cannot prevent connection preparation.

## Written material

- [Tutorial](../tutorials/step-03-authorization-and-roles.md): a complete standalone program, actual answers and the full chapter scenario map.
- [Migration guide](../how-to/roles-and-object-rules.md): declaration migration, caller context, shared limits and execution timing.
- [Reference](../reference/access-control.md): role forms, invariants, exact refusals, gate payloads and graph exports.
- [Intent invariants](../reference/intents-and-invariants.md), [glossary](../reference/glossary.md), [action guide](../how-to/authoring-action.md) and [contents](../index.md): aligned terminology and navigation.

The focused teaching scenarios are paired scripts and notebooks:

| Topic | Script | Notebook |
| --- | --- | --- |
| Caller attributes | [02](../../examples/step_03_authorization_and_roles/02_object_rule.py) | [02](../../examples/step_03_authorization_and_roles/02_object_rule.ipynb) |
| Shared input limit | [03](../../examples/step_03_authorization_and_roles/03_shared_object_rule.py) | [03](../../examples/step_03_authorization_and_roles/03_shared_object_rule.ipynb) |
| Query versus execution | [07](../../examples/step_03_authorization_and_roles/07_three_answers.py) | [07](../../examples/step_03_authorization_and_roles/07_three_answers.ipynb) |
| Refusal short-circuit | [13](../../examples/step_03_authorization_and_roles/13_cascade.py) | [13](../../examples/step_03_authorization_and_roles/13_cascade.ipynb) |
| Guests, active roles and object refusals | [14](../../examples/step_03_authorization_and_roles/14_guest_and_any.py) | [14](../../examples/step_03_authorization_and_roles/14_guest_and_any.ipynb) |
| Silenced descendant | [16](../../examples/step_03_authorization_and_roles/16_silenced_role.py) | [16](../../examples/step_03_authorization_and_roles/16_silenced_role.ipynb) |
| Branch ordering | [17](../../examples/step_03_authorization_and_roles/17_branch_order.py) | [17](../../examples/step_03_authorization_and_roles/17_branch_order.ipynb) |
| Branch reasons | [22](../../examples/step_03_authorization_and_roles/22_reason_in_branch.py) | [22](../../examples/step_03_authorization_and_roles/22_reason_in_branch.ipynb) |
| Role declarations and migration failures | [24](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py) | [24](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.ipynb) |
| Graph representation | [25](../../examples/step_03_authorization_and_roles/25_access_graph.py) | [25](../../examples/step_03_authorization_and_roles/25_access_graph.ipynb) |

All 26 chapter scripts were executed, including the neighboring lessons linked
from the tutorial. All 26 notebooks were refreshed from their paired scripts and
executed in fresh Python processes. Earlier notebook cells with missing imports
were corrected. Each code cell has an actual execution count and saved output;
the combined stdout exactly matches the corresponding script.

Execution used direct sequential Python-cell execution with top-level await,
not a Jupyter kernel. The repository environment did not provide the Jupyter
execution libraries. This verifies the cell code and its order, but does not
claim verification of Jupyter UI or kernel integration. Reproduce the comparison
with `.venv/bin/python docs/reports/evidence/role_access_notebooks.py`.
The [runner](evidence/role_access_notebooks.py) and
[per-scenario actual outputs](evidence/role-access-execution.json) are saved.

## Checks and adversarial evidence

The complete `aoa-action-machine` suite passed: **2994 tests**. The first sandboxed
run had three failures because local socket binding was forbidden. With permission
for local sockets, the full rerun passed in 28.83 seconds; the JWT-only rerun also
passed all 31 tests. These were environment restrictions, not established code
faults. A further focused run of graph, refusal and runtime tests passed 52 tests.

Ruff passed for the package source, package tests, chapter scripts/notebooks and
new verification runners. Formatting passed for the changed scripts and runners.
Mypy reported no issues in 345 package source files. Complete Python blocks in
the new guide and rewritten tutorial were copied into clean temporary files and
executed; their stdout was compared with the published output. Local file and
heading links were checked in all eight changed documentation pages: 251 local links and two standalone programs passed. The [documentation runner](evidence/role_access_documentation.py) and its [results](evidence/role-access-documentation.json) make that check repeatable.

The [adversarial runner](evidence/role_access_adversarial.py) performs five
independent in-memory mutations in fresh child processes:

| Temporary break | Failing guarantee | Passing neighbor |
| --- | --- | --- |
| Ignore condition keyword rejection | Migration lesson must refuse removed keywords | Ordinary graph declaration |
| Restore silenced roles to the matching set | Silenced manager descendant must be refused | Active role match |
| Recognize guests only as a lone spec | Guest alternative must admit an anonymous caller | Lone guest declaration |
| Bypass the declared object rule | A closed object must refuse a guest | Active role match |
| Put condition data back on role edges | Role-edge properties must be empty | Active role match |

Each baseline had **2 passed**. Each mutation had exactly **1 failed, 1 passed**.
Only child-process function code was replaced. No repository source was changed
for these mutations. See the [actual pytest outputs](evidence/role-access-mutations.json).
Run `.venv/bin/python docs/reports/evidence/role_access_adversarial.py` to repeat.

## A real call

Command:

```sh
.venv/bin/python examples/step_03_authorization_and_roles/03_shared_object_rule.py
```

Actual stdout:

```text
amount 50: {'kind': 'allowed'}
amount 150: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'AMOUNT_LIMIT'}
```

The migration is from an unconditional `grant(Role)` wrapper to `Role`, and from
conditions beside that role to branches of an async object rule. In particular,
a former guard refusal now names `ACCESS_DECIDE` and occurs after connection
validation. The amount lesson checks both the accepted and refused neighbor.

## Limits and remaining work

No additional implementation defect was established within this verification
boundary. That is not a proof of full correctness. No production identity
provider, database, external service, other package suite, browser or frontend
build was exercised. The repository-wide check script was not run because it
would violate the requested scope. The package checks above replace that run
for this documentation task; no claim of a repository-wide green run is made.

Future verification can exercise these same notebooks through an installed
Jupyter kernel and run the broader integration checks in a separately authorized
scope. No source correction is required by the measured examples. The remaining
step for this prepared change is maintainer review; publishing requires a
separate instruction.
