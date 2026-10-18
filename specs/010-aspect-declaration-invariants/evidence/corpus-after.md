# Corpus after the migration — what the rules refuse now, and what is left

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T036 | **Date**: 2026-10-18

**Base commit for the comparison**: `d10c6ef9` (the tree the baseline in `corpus-baseline.md` was measured on).

## The scan

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py
```

```text
| Tree | Files | Declarations | Conforming | Non-conforming | of them asserted refusals | to migrate |
| --- | --- | --- | --- | --- | --- | --- |
| packages (**/*.py) | 1217 | 375 | 359 | **16** | 16 | 0 |
| examples (**/*.py) | 157 | 171 | 168 | **3** | 3 | 0 |
| examples (**/*.ipynb) | 155 | 166 | 163 | **3** | 3 | 0 |
| docs (**/*.md, ```python blocks) | 86 | 99 | 98 | **1** | 1 | 0 |
| **total** | | **811** | **788** | **23** | **23** | **0** |

| Declaration | Total | Non-conforming |
| --- | --- | --- |
| `@summary_aspect` | 551 | 8 |
| `@regular_aspect` | 189 | 6 |
| `@on_error` | 30 | 1 |
| `@compensate` | 41 | 8 |

| Fault | Declarations |
| --- | --- |
| names | 9 |
| annotations | 18 |
| return | 12 |
| positional | 2 |

Fault combinations (a declaration can carry several):

| Combination | Declarations |
| --- | --- |
| none | 788 |
| annotations | 7 |
| annotations+return | 6 |
| names+annotations+return | 5 |
| names | 2 |
| names+positional | 2 |
| return | 1 |

Notebooks carrying declarations: 77

- `examples/domain_model/01_domain_model.ipynb`
- `examples/extensions/01_opentelemetry.ipynb`
- `examples/how_to/01_custom_adapter.ipynb`
- `examples/how_to/03_custom_plugin.ipynb`
- `examples/how_to/04_custom_logger.ipynb`
- `examples/how_to/05_custom_cache_adapter.ipynb`
- `examples/how_to/07_extend_context.ipynb`
- `examples/how_to/08_custom_intent.ipynb`
- `examples/research_self_knowledge/01_self_audit.ipynb`
- `examples/step_01_Action_and_pipeline/01_hello_world.ipynb`
- `examples/step_01_Action_and_pipeline/02_params_result_and_box.ipynb`
- `examples/step_01_Action_and_pipeline/03_multiple_aspects.ipynb`
- `examples/step_01_Action_and_pipeline/04_inheritance.ipynb`
- `examples/step_01_Action_and_pipeline/05_aspect_declarations.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/01_checkers.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/07_opaque.ipynb`
- `examples/step_03_authorization_and_roles/01_roles.ipynb`
- `examples/step_03_authorization_and_roles/02_grant.ipynb`
- `examples/step_03_authorization_and_roles/03_guard.ipynb`
- `examples/step_03_authorization_and_roles/04_access_decide.ipynb`
- `examples/step_03_authorization_and_roles/05_machine_check.ipynb`
- `examples/step_03_authorization_and_roles/06_the_declaration.ipynb`
- `examples/step_03_authorization_and_roles/07_three_answers.ipynb`
- `examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb`
- `examples/step_03_authorization_and_roles/09_reasons.ipynb`
- `examples/step_03_authorization_and_roles/10_context_in_the_check.ipynb`
- `examples/step_03_authorization_and_roles/11_events.ipynb`
- `examples/step_03_authorization_and_roles/13_cascade.ipynb`
- `examples/step_03_authorization_and_roles/14_guest_and_any.ipynb`
- `examples/step_03_authorization_and_roles/15_alternative_roles.ipynb`
- `examples/step_03_authorization_and_roles/16_silenced_role.ipynb`
- `examples/step_03_authorization_and_roles/17_grant_fallback.ipynb`
- `examples/step_03_authorization_and_roles/21_failure_event.ipynb`
- `examples/step_03_authorization_and_roles/23_invalid_answer.ipynb`
- `examples/step_04_saga_and_compensations/01_saga_compensate.ipynb`
- `examples/step_05_error_handling/01_on_error.ipynb`
- `examples/step_06_dependencies/01_depends.ipynb`
- `examples/step_07_context/01_context.ipynb`
- `examples/step_07_context/02_env.ipynb`
- `examples/step_08_cache/01_cache.ipynb`
- `examples/step_09_plugins/01_ocel.ipynb`
- `examples/step_10_logs/01_logging_sensitive.ipynb`
- `examples/step_13_fastapi/01_service.ipynb`
- `examples/step_13_fastapi/02_auth_override.ipynb`
- `examples/step_13_fastapi/03_login_action.ipynb`
- `examples/step_13_fastapi/04_bearer_auth.ipynb`
- `examples/step_13_fastapi/05_cookie_auth.ipynb`
- `examples/step_13_fastapi/06_jwks_auth.ipynb`
- `examples/step_14_langgraph/01_external_connection.ipynb`
- `examples/step_14_langgraph/01_langgraph.ipynb`
- `examples/step_14_langgraph/02_inline_graph.ipynb`
- `examples/step_14_langgraph/03_function_node.ipynb`
- `examples/step_14_langgraph/04_field_mapping.ipynb`
- `examples/step_14_langgraph/05_testing.ipynb`
- `examples/step_14_langgraph/06_field_mapping.ipynb`
- `examples/step_14_mcp/01_tool.ipynb`
- `examples/step_14_mcp/02_bearer_auth_limitation.ipynb`
- `examples/step_16_complex_input/01_complex_input.ipynb`
- `examples/step_17_connections/01_connections.ipynb`
- `examples/step_17_connections/02_per_call.ipynb`
- `examples/step_17_connections/14_fastapi_lifespan.ipynb`
- `examples/step_17_connections/15_mcp_call.ipynb`
- `examples/step_17_connections/16_pool_lifespan.ipynb`
- `examples/step_18_converters/01_versions.ipynb`
- `examples/step_19_resource/01_resource.ipynb`
- `examples/step_19_resource/02_refusal.ipynb`
- `examples/step_19_resource/03_substitution.ipynb`
- `examples/step_19_resource/07_nested_action.ipynb`
- `examples/step_23_testbench/01_testbench.ipynb`
- `examples/step_24_substitution/01_substitution.ipynb`
- `examples/step_25_context/01_context.ipynb`
- `examples/step_26_maxitor/01_graph.ipynb`

Documentation pages carrying declarations: 26

- `docs/explanation/system-altitudes.md`
- `docs/explanation/verification-must-be-independent.md`
- `docs/explanation/verification-must-be-independent_draft.md`
- `docs/extensions/langgraph.md`
- `docs/extensions/ocel.md`
- `docs/how-to/authoring-action.md`
- `docs/how-to/authoring-adapter.md`
- `docs/how-to/authoring-adapter.ru_draft.md`
- `docs/how-to/authoring-context-extension.md`
- `docs/how-to/migrating-legacy.md`
- `docs/reference/intents-and-invariants.md`
- `docs/reference/intents-and-invariants.ru_draft.md`
- `docs/research/environment-context-port.md`
- `docs/tutorials/step-01-action-and-pipeline.md`
- `docs/tutorials/step-02-state-as-x-ray.md`
- `docs/tutorials/step-03-authorization-and-roles.md`
- `docs/tutorials/step-03-authorization-and-roles.ru_draft.md`
- `docs/tutorials/step-04-saga-and-compensations.md`
- `docs/tutorials/step-05-error-handling.md`
- `docs/tutorials/step-06-dependencies.md`
- `docs/tutorials/step-07-context.md`
- `docs/tutorials/step-09-plugins.md`
- `docs/tutorials/step-17-connections.md`
- `docs/tutorials/step-17-connections.ru_draft.md`
- `docs/tutorials/step-19-resource.md`
- `docs/tutorials/step-19-resource.ru_draft.md`

Files to migrate
```


## How each tree got here

| Tree | Before | After | What moved it |
| --- | --- | --- | --- |
| `packages/` | 80 non-conforming, 19 deliberate | 16 non-conforming, all deliberate | phase 3 migrated 61 by codemod and by renaming a parameter in place; phase 4 replaced 256 `Any` annotations with the contract types |
| `examples/**/*.py` | 163 non-conforming | 3, all in the new declaration example and marked deliberate | 163 declarations: 160 by the same codemod, 3 renamed (`p, s, b, c`), and the dotted annotations of the classes under construction quoted, because those files carry no `from __future__ import annotations` |
| `examples/**/*.ipynb` | 158 non-conforming | 3, the same cases in its notebook twin | 86 code cells across 73 notebooks, cell by cell; one notebook (`how_to/02_custom_auth_coordinator.ipynb`) was left untouched because it splits a single import across two cells and holds no aspect declarations |
| `docs/**/*.md` | 98 non-conforming | 1, marked deliberate | the documentation step (T039): 78 blocks migrated, and the one remaining block is a research sketch that says in a comment what it is |

The 16 that remain in `packages/` are the tests of the rule: each lives inside a `pytest.raises`
block that asserts the refusal it demonstrates. The file lists them by path and line.

## The examples still run

Every example script was run twice: once from a pristine worktree at `d10c6ef9` with that tree's own
sources, and once from the migrated tree. Same interpreter, same session.

```text
before: 156 scripts, 150 exit 0, 6 non-zero
after:  156 scripts, 150 exit 0, 6 non-zero
```

- **No script regressed**: every script that exited 0 before still exits 0.
- **The six that fail, failed before** — they need services or extras this machine does not provide
  (Postgres, a live MCP server), and the failure is the same one.
- **Output differs only where it is not deterministic**: order ids, trace and span ids, JWT tokens,
  measured durations, and the absolute path an example prints for the file it writes. Three scripts
  differ in those values alone; nothing user-visible changed.

## What the scan cannot see

The scan judges the declaration's shape and the presence of annotations. It does not resolve the
types — that needs the operation assembled, and it is covered by the suites (2617 engine tests plus
674 across the other packages, all passing after this phase).

## Two markers a documentation block can carry

A documentation snippet has no test around it, so the scan cannot tell a mistake from an
explanation of a mistake by looking at the code. Rather than let those blocks sit in the scan's
"to migrate" column for ever, the scan reads two comments a block can carry:

```python
# expected-refusal: NamingSuffixError   — the block demonstrates a refusal on purpose
# design sketch: ...                    — the block is a proposed API, not the current one
```

A block carrying either is counted with the deliberate refusals, never as work left undone — and the
same marker works in Python, within eight lines of the declaration, which is how the seven cases of
`examples/step_01_Action_and_pipeline/05_aspect_declarations.py` and of its notebook say what they are. That
is the same principle the pytest fixtures follow: a declaration that is wrong says so, in the
place where it is wrong, in words a machine can read.
