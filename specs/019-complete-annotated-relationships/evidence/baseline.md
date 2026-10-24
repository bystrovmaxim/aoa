# Baseline Reproduction: Complete Annotated Relationships

**Task**: T002 (Procedure 1 — Setup and scoped evidence)
**Date**: 2026-10-24
**Baseline commit**: `617b05d9b409d9d7d5da80fca5a67e65a03a02c2`
(`Merge pull request #257 from bystrovmaxim/feature/issue-256-dictionary-reference`, 2026-10-23 23:07:22 +0300)

## Six-file baseline command

Reproduced from `quickstart.md`, run against the existing `.venv` in importlib mode:

```sh
.venv/bin/python -m pytest --import-mode=importlib \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_containers.py \
  packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py \
  packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py \
  packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py -q
```

**Actual result** (2026-10-24):

```text
107 passed in 0.77s
```

The planning-time `107 passed in 0.90s` is confirmed; wall time differs (0.77s) but the
count is unchanged. These six files encode the old behavior and must migrate; a green
baseline is not acceptance of the new feature.

## Dependency versions (captured from the working `.venv`)

| Package | Version |
| --- | --- |
| Python | 3.12.12 |
| pydantic | 2.12.5 |
| pydantic_core | 2.41.5 |
| pytest | 8.4.2 |
| duckdb | 1.5.2 |

No dependency upgrade is required for the design.

## Fixture import audit (six-file closure)

The six files import from `packages/aoa-action-machine` (domain, graph, intents, model) and
`packages/aoa-maxitor` (tests only). Their import closure was audited for the forbidden
boundaries during the reproduction: no `packages/aoa-demo` code and no `*_draft.md`/`*.ru*`
artifact is imported. `test_entity_field_validator.py` imports the shared
`...support.domain_model.entities` fixture (DraftLifecycle / DraftStateEntity), which is a
permitted action-machine test fixture.

## Compatibility/classifier evidence

The 107-test result alone is not the compatibility baseline. The selected existing
compatibility/classifier controls and their actual pre-change outcomes are captured in
`compatibility-baseline.json` (this directory), produced from the same `.venv` and commit:

| Partition | Command (suffix) | Result |
| --- | --- | --- |
| Specialization/classifier rules | `test_entity_specialization_rules_axis.py test_entity_specialization_rules_global.py test_entity_specialization_sweep.py test_entity_specialization_graph.py test_entity_specialization_vocabulary.py test_graph_json_schema_specialization.py` | `65 passed in 0.73s` |
| Generalization edge / coordinator / resolver | `test_entity_specialization_rules_global.py test_node_graph_coordinator_generalization_integration.py test_generalization_graph_edge.py test_specialized_graph_edges.py test_node_graph_coordinator_generalization.py test_graph_json_schema_generalization.py test_entity_specialization_resolver.py` | `45 passed in 0.13s` |

These partitions are what FR-010 ("preserve existing relationship compatibility") means in
the current code. `compatibility-baseline.json` distinguishes the checks actually implemented
from docstring-only claims (the ownership/container-pair matrix named in
`relation_containers.py` and `relation_markers.py` docstrings is not implemented as code).
