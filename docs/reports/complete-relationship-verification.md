# Complete relationship documentation verification

Verified on 2026-10-24 in the existing working tree of `feature/issue-259-complete-annotated-relationships`. The comparison base is `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`, the merge base with `origin/main`. There are no branch commits beyond that base; the implemented change is in the working tree. Committed, staged, unstaged and relevant untracked changes were considered together. Production behavior was not edited during this documentation work.

The implementation context is [the complete-declaration issue](https://github.com/bystrovmaxim/aoa/issues/259), following [dictionary reference declarations](https://github.com/bystrovmaxim/aoa/issues/256). Requirements are distinguished below from observed behavior.

## Confirmed defects

### Explicit overrides

An unchanged inherited relationship correctly retains the base endpoint. An explicit redeclaration with an identical resolved annotation and markers should instead introduce a new endpoint. After rebuilding every model, the redeclaration is accepted even though the reverse field still targets the base. The existing override test does not rebuild those forward references, so it does not establish the resolved override guarantee.

[Minimal public-API reproduction](evidence/relationship_override.py).

```sh
.venv/bin/python docs/reports/evidence/relationship_override.py
```

Actual stdout:

```text
Unchanged inherited endpoint: accepted (expected)
Explicit same-signature override: accepted (defect)
```

Expected: `EntityFieldDeclarationError` for the explicit override; unchanged inheritance must continue to pass. Next step: distinguish an explicit redeclaration from an inherited field and add a rebuilt public-API regression.

### Association serialization schema

[Minimal public-API reproduction](evidence/association_export_schema.py).

```sh
.venv/bin/python docs/reports/evidence/association_export_schema.py
```

Actual stdout:

```text
Export: {'selection': {'code': 'one', 'display_name': 'One', 'properties': {'count': 1}}}
Association properties schema: {'type': 'object'}
Standalone count type: integer
```

Expected: the association serialization schema retains the dictionary's typed emitted properties and referenced definitions. Actual: export is correct, but nested properties are only an object. Next step: preserve the standalone dictionary serialization contract through the association schema and test an invalid custom-property payload against it.

### Dictionary fields in Maxitor

[Minimal public-API reproduction](evidence/dictionary_erd.py).

```sh
.venv/bin/python docs/reports/evidence/dictionary_erd.py
```

Actual stdout:

```text
{'code': 'eur', 'display_name': 'Euro', 'properties': [{'name': 'symbol', 'value': '€'}]}
CurrencyEnumEntity
Currency field rows: 2
Relation: currency (one) -> CurrencyEnumEntity
```

Expected: one payload field per entity/field name, preserving the retained field identity, type, ordering and reference hint while adding FK information. Actual: the public summary returns a retained field row plus a synthesized FK row. Next step: merge those rows and test the complete graph-to-payload path; do not discard the retained metadata.

### Specialization directions

[Minimal public-API reproduction](evidence/specialization_direction.py).

```sh
.venv/bin/python docs/reports/evidence/specialization_direction.py
```

Actual stdout:

```text
Generalization Inverse paired with Specialization NoInverse: accepted (defect)
```

Expected: an inverse endpoint cannot pair with a `NoInverse` endpoint. Actual: the full public machine builds for this specialization/generalization pair. Next step: validate reciprocal directions for specialization endpoints while retaining classified-axis checks and accepted ordinary one-way links.

## Executed checks

The [recorded results](evidence/relationship-verification-results.json) list every changed script and notebook, execution counts, standalone documentation blocks, scoped test summaries and adversarial outcomes.

- 34 changed/new numbered scripts completed successfully in fresh Python processes.
- Their 34 notebooks executed directly as Python cells, each in a fresh process. Every code cell has its actual execution count and captured output; concatenated stdout equals its script's stdout. Jupyter kernel execution was not used because the environment lacks the Jupyter execution dependencies.
- The focused action-machine suite passed 100 tests: dictionary association input/schema/graph, field completeness, inverse validation, separate-module resolution, publication entry points, breaking-form migration, source placement and compatibility regressions.
- The additional descriptor/unchanged-control/specialization-axis suite passed 30 tests and failed one diagnostic expectation, described below.
- Maxitor dictionary payload and DuckDB query tests passed 18 tests. These existing tests do not catch the duplicate-row reproduction above.
- Ruff lint passed for the action-machine source and tests and for changed examples/evidence. Formatting was checked for changed examples, notebooks and evidence. The assignment-side Field checker passed on the positive selection/direction/stereotype/cross-module examples and their endpoint modules.
- 18 standalone Python blocks from the changed guides/tutorials were copied to clean files and executed separately. All 18 shown output snapshots matched actual stdout. Local links and header anchors were checked without following excluded-language targets.

The focused action-machine command lists these modules under `packages/aoa-action-machine/tests/action_machine/`: `domain/test_dictionary_association.py`, `domain/test_dictionary_association_schema.py`, `graph/test_entity_inverse_validator.py`, `graph/test_entity_inverse_cross_module.py`, `graph/test_dictionary_association_graph.py`, `graph/test_entity_field_validator.py`, `graph/test_entity_declaration_entrypoints.py`, `graph/test_complete_relationship_migration.py`, `graph/test_entity_field_source_check.py` and `graph/test_relationship_compatibility_regressions.py`. Each pytest invocation used `.venv/bin/python -m pytest --import-mode=importlib ... -q`.

### Existing diagnostic assertion failure

This additional command was executed independently:

```sh
.venv/bin/python -m pytest --import-mode=importlib packages/aoa-action-machine/tests/action_machine/intents/entity/test_resolved_entity_fields.py packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_unchanged_controls.py packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py -q
```

Result: `1 failed, 30 passed`. `test_an_alternative_paired_through_another_field_name_is_refused` expects `but the axis names`, but the implementation now refuses the missing reverse direction first:

```text
Specialization 'pack' on entity 'WronglyPairedHeadCoreEntity' is invalid: the head names inverse field 'other', but alternative 'WronglyPairedSpecEntity' declares no Inverse on 'rec'; declare a reciprocal Inverse(field_name=...) on both endpoints.
```

Next step: migrate that fixture so it reaches the intended wrong-field rule, retaining a separate regression for missing reverse directions. This test failure was not hidden or fixed by changing production behavior.

## Adversarial checks

The [isolated regression harness](evidence/relationship_adversarial.py) checks six guarantees, including a valid neighboring case. It changes behavior only inside its disposable Python process; no source file is patched. Run the unmodified control with:

```sh
.venv/bin/python -m pytest docs/reports/evidence/relationship_adversarial.py -q
```

The control passed all six tests. Each temporary regression failed exactly its intended test, leaving the other five green:

| `AOA_DOCS_MUTATION` | Reintroduced behavior | Result |
| --- | --- | --- |
| `bare` | Bare structural entity accepted | 1 failed, 5 passed |
| `embedded` | NoRelation entity embedding accepted | 1 failed, 5 passed |
| `inverse` | One-sided ordinary inverse accepted | 1 failed, 5 passed |
| `dictionary` | Raw dictionary member accepted without wrapper | 1 failed, 5 passed |
| `graph` | Dictionary omitted from ordinary association projection | 1 failed, 5 passed |

For example, prefix the control command with `AOA_DOCS_MUTATION=inverse` to reproduce the expected failing regression. These are isolated behavioral reversions, not a complete checkout of the previous version. They establish sensitivity of these specific assertions, not completeness of all tests.

## Limits and next work

The aggregate repository check, complete package test suites, mypy/pylint, packaging builds and client rendering/build were not run. The aggregate check would exceed the authorized package scope. Passing scoped tests is not a claim that the full repository is green. Existing implementation evidence also records an incomplete broader test-corpus migration; it was not replaced with invented successful results.

Correct the four reproduced implementation gaps and migrate the remaining test fixtures in a separate code change. Then run the wider authorized compatibility checks. Source and staging state were preserved; no commit, push, pull request or merge was performed. Russian documents and drafts were neither created nor validated.
