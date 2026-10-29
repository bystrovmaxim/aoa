# Endpoint role verification

Verified on 2026-10-25 against the existing working tree of `codex/issue-261-complete-relationships`. The main branch is `origin/main`; its merge base with HEAD is `53171199d4953aaaa35514e0c772766006942d27`. HEAD before this documentation pass was `afa539898bb22576c818c20591f8ae40ac855483`.

The comparison covered base → current working tree: the two branch commits and their messages, committed specification changes, staged implementation/documents/examples, unstaged changes and relevant untracked paths. The branch commits are specification work for role declarations and endpoint compatibility; the runtime change under review was staged. Existing staged README metadata updates were preserved. Production source was not modified. No commands to change staging were issued. The final comparison detected that the index had changed during the session; its current content was retained without resetting or restoring it.

The feature source is [the endpoint compatibility issue](https://github.com/bystrovmaxim/aoa/issues/261). The earlier dictionary reference issue is context, not evidence of implemented behavior. The [recorded results](evidence/endpoint-role-results.json) contain hashes, per-scenario outputs, code-cell counts, documentation results, adversarial output and public-API reproductions.

## Verified behavior and evidence

| User-visible contract | Evidence |
| --- | --- |
| The eight roles form a symmetric matrix: 22 directed permitted cells and 42 refused cells | Existing matrix tests; real declaration tests for permitted and prohibited families; public projection in scenarios 68–71 |
| Ordinary reciprocal pairs permit association/association or one Aggregate/Composite endpoint opposite an association | Role assembly tests, full package suite, scenarios 68–70 and isolated ownership/Many regressions |
| Specialized roles pair exclusively with each other | Matrix and specialized-declaration tests, classified-axis scenario 71 and isolated specialized regression |
| NoInverse means independent ordinary links; it cannot be an Inverse target | Direction tests and scenario 73, asserting actual graph direction metadata |
| NoInverse on either specialized role is now refused | Declaration tests and scenario 71 with exact EntityFieldDeclarationError text; this closes the earlier NoInverse acceptance gap |
| All six ordinary dictionary containers normalize canonical members, retain their class and graph family/cardinality | Existing dictionary-container tests, scenario 72, dictionary/member adversarial checks |
| Many dictionary input is an array of id objects; export is an array of canonical references | Transport/schema tests and scenario 72 with real serializers, repeated codes, empty and absent cases |
| A role mismatch has the new public RoleCompatibilityError contract | Existing diagnostic tests and exact string assertions in scenarios 69–71 |

The matrix counts are counts of role combinations, not a claim that all 64 cells were instantiated as complete public classified models. Existing tests enumerate the full matrix and use real declarations for representative families. The examples use public graph projection; scenario 68 also builds the full machine. The complete role table is documented in the [reference](../reference/intents-and-invariants.md#endpoint-role-compatibility), with migration and actual outputs in the [how-to](../how-to/relationship-role-compatibility.md).

## Confirmed gaps requiring code work

### Typed custom-property schemas

Relationship values export correctly, including custom serializers, but relationship serialization schemas describe nested properties only as an object. An exported integer property can be replaced with a string and still pass the schema. Both One and Many are affected. A standalone dictionary schema still describes that property as an integer.

[Public-API reproduction](evidence/endpoint_dictionary_boundaries.py):

```sh
.venv/bin/python docs/reports/evidence/endpoint_dictionary_boundaries.py
```

The first result is:

```text
Wrong custom-property types accepted by One and Many export schemas (defect)
```

Expected: the relationship schema retains emitted custom-property types and their referenced definitions, so malformed properties fail schema validation. Next step: preserve that typed schema for each wrapper/cardinality and add invalid-output schema regressions. The current documentation states the limitation rather than claiming typed properties are implemented.

### Dictionary reverse endpoints

The dictionary-specific blanket rejection of Inverse was removed, but a real reverse relationship cannot currently be declared on the catalogue: its immutable-property check refuses the container annotation while Python creates the dictionary class. The reproduction declares a matching forward endpoint, then attempts its complete reverse field.

The same reproduction prints this exact class-creation refusal:

```text
ValueError: ReverseEnumEntity: field 'host' is AssociationOne, which a dictionary value cannot carry; supported: str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of a supported type, or a tuple of supported types.
```

Expected by the feature: a complete reciprocal ordinary dictionary relationship follows the same inverse and role rules as other targets. Next step: reconcile relationship-valued catalogue fields with member construction, immutability, serialization and deferred rebuilding, then add a fully declared reciprocal dictionary model. Do not describe the current earlier refusal as a new NoInverse-only role policy. Successful one-way dictionary targets do not prove this reciprocal path.

### Dictionary field rows in the ERD

The public summary carries all three ordinary relationship families, but returns two field rows for each of the six declared dictionary fields: the retained field plus a synthesized FK row. The source graph itself has six ordinary relationship edges without special reference edges.

[Public graph-to-summary reproduction](evidence/endpoint_dictionary_erd.py):

```sh
.venv/bin/python docs/reports/evidence/endpoint_dictionary_erd.py
```

Actual output:

```text
Rows per declared field: {'primary': 2, 'quoted': 2, 'snapshot': 2, 'alternatives': 2, 'available': 2, 'bundled': 2}
Relation families: ['aggregation', 'association', 'composition']
```

Expected: one payload field per entity/field name, keeping its identity, type, ordering and reference hint and enriching it with FK metadata. Next step: merge those rows and test the full graph-to-consumer path across One/Many and the three role families. This reproduction does not establish a frontend rendering result.

### Custom container subclasses

A container subclass retaining composition meaning can bypass role comparison. A reciprocal pair using that subclass opposite CompositeMany builds the full public machine. The supplied eight roles are covered; this accepted subclass must not be advertised as a ninth role or as permission for ownership/ownership.

[Public machine reproduction](evidence/endpoint_role_subclass.py):

```sh
.venv/bin/python docs/reports/evidence/endpoint_role_subclass.py
```

Actual output:

```text
Custom composition / composition: machine built (validation gap)
```

Expected: either classify the subclass under its supplied base role and reject the incompatible pair, or explicitly refuse an unsupported role before publication. Silently skipping compatibility is incorrect. Next step: add a public assembly regression for this declaration before choosing the supported-extension policy. No production source was patched to conceal the gap.

## Executed tests and scoped checks

The complete action-machine package test command was:

```sh
.venv/bin/python -m pytest --import-mode=importlib packages/aoa-action-machine/tests -q
```

In the sandbox it returned `3 failed, 3042 passed`. All three failures were `PermissionError: [Errno 1] Operation not permitted` while binding a test HTTP server to 127.0.0.1. They occurred before the intended JWT assertions. The three affected tests were rerun with localhost access:

```sh
.venv/bin/python -m pytest --import-mode=importlib packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py::test_jwks_endpoint_truly_unreachable_returns_none packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py::test_jwks_malformed_json_response_returns_none packages/aoa-action-machine/tests/action_machine/auth/jwt_auth/test_jwt_authenticator.py::test_jwks_wrong_shaped_json_response_returns_none -q
```

The retry returned `3 passed`. Thus all 3045 package tests passed across the initial run and the targeted permission retry; this was not a single unrestricted full-suite invocation.

The focused role/matrix/dictionary/completeness suite separately passed 121 tests. The full Maxitor package command returned `154 passed, 1 skipped, 1 xfailed`:

```sh
.venv/bin/python -m pytest --import-mode=importlib packages/maxitor/front/tests -q
```

All 113 numbered scripts in the two dictionary/relationship tutorial directories passed. Nine changed/new script/notebook pairs were executed in fresh processes: six coherent role scenarios and three earlier selection scenarios whose exact diagnostics changed. Every notebook has real outputs and execution counts, with stdout equal to its script. Cells were executed directly as Python, not through a Jupyter kernel; the kernel dependencies were unavailable.

19 standalone Python blocks in the changed guides/tutorials were copied to clean files and executed. All shown output snapshots matched. Local links and heading anchors were checked. Ruff lint passed on the package source/tests and the changed examples/evidence; formatting was checked for changed scripts, notebooks and evidence. The assignment-side Field checker passed on all six role scenarios.

## Actual adversarial reversions

The [isolated harness](evidence/endpoint_role_adversarial.py) changes behavior only in a disposable Python process, without editing source files. The unmodified control passes six tests. Each temporary reversion fails exactly its targeted test while the other five pass:

| AOA_ROLE_MUTATION | Restored faulty behavior | Result |
| --- | --- | --- |
| ownership | Permit composition/composition | 1 failed, 5 passed |
| specialized | Permit generalization/generalization | 1 failed, 5 passed |
| many | Reject AggregateMany/AssociationOne | 1 failed, 5 passed |
| dictionary | Restore AssociationOne-only dictionary target acceptance | 1 failed, 5 passed |
| member | Accept an unknown dictionary code | 1 failed, 5 passed |

Run the control with:

```sh
.venv/bin/python -m pytest docs/reports/evidence/endpoint_role_adversarial.py -q
```

Prefix it with the selected environment value, for example `AOA_ROLE_MUTATION=ownership`, to reproduce the expected failing regression. These are deliberate behavioral reversions, not a historical checkout. They demonstrate sensitivity of the selected assertions, not complete correctness of the implementation.

## Verification limits

The aggregate repository check was not run because it exceeds the authorized package scope and applies automatic source fixes. Tests for other packages, mypy/pylint, distribution builds and the client build/render were not run. Existing skips and expected failures retain their original outcomes. No full-repository green claim is made.

The four reproduced gaps require code work separate from this documentation-only pass. Documentation and examples describe the observed behavior and the intended correction separately. Production code and the constitution were preserved. No staging commands were issued, and the current index was left intact after the detected index change. No commits, pushes, pull requests or merges were performed.
