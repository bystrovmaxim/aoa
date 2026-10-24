# Validation Guide: Complete Annotated Relationships

## Scope and prerequisites

Use the existing repository .venv and the current feature branch. Commands below start at the repository root unless a working directory is specified. Do not run the workspace-wide check script. Audit each expanded test/script import closure before running it: excluded package code and Russian/draft files must never be read, executed or checked.

This is a planning guide. The baseline below ran; implementation acceptance scenarios below have not yet run and are not claimed as passing.

## Current baseline — executed during planning

```sh
.venv/bin/python -m pytest --import-mode=importlib   packages/aoa-action-machine/tests/action_machine/domain/test_relation_containers.py   packages/aoa-action-machine/tests/action_machine/domain/test_relation_markers.py   packages/aoa-action-machine/tests/action_machine/graph/test_entity_field_validator.py   packages/aoa-action-machine/tests/action_machine/graph/test_entity_reference_graph.py   packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py   packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py -q
```

Actual result on 2026-10-24:

```text
107 passed in 0.90s
```

These existing tests encode old behavior and must migrate. A green baseline is not acceptance of the new feature.

Before implementation changes, task T002 must additionally capture selected existing compatibility/classifier cases and actual outcomes in `evidence/compatibility-baseline.json`, including case inputs, commands, baseline commit/source hashes and both endpoint orientations where relevant. The 107-test result alone is not that compatibility baseline; later regression tests must compare to the recorded pre-change outcomes.

## Implementation acceptance — execute after the code and fixture migrations

### 1. Complete declarations and inverse resolution

Use the migrated validator/marker tests and focused reciprocal-inverse tests added during implementation. Exercise Core, Assoc, Detail, Spec and Enum as permitted owner/target; keep State controls. Supply one complete declaration and all incomplete forms per topic. Require exact errors at the documented boundary.

Run the two-module inverse teaching scenario in fresh subprocesses for both import orders after explicit model_rebuild namespace resolution. Check missing markers, duplicate markers, wrong explicit targets, missing/nonreciprocal reverse fields and unresolved names. Validate coordinator/factory/machine and supported direct projection paths independently. Verify a valid Base/Item reciprocal pair remains valid for unchanged inherited Child fields; check explicit/semantic overrides as new endpoints, grandchild and diamond/MRO cases, and independent graph projection for each effective host. Use the declaring-owner rules in the declaration contract; do not auto-retarget a base pair or accept arbitrary subclass matches.

Expected result: complete declarations pass; the same new refusal is detected through every supported publication path. Existing compatibility checks retain their behavior; no matrix-based refusal appears.

### 2. Dictionary runtime and both schema modes

Follow [dictionary-association.md](contracts/dictionary-association.md). Use an explicit Python AssociationOne instance and a JSON id container. Verify canonical identity and new frozen wrapper creation, unknown/foreign/fabricated/mismatched refusal, nullable omission rules, JSON reference output and handler-resolved definitions with custom serializers.

Expected result: host-field Python values remain containers, their entity is canonical, JSON output equals to_reference(), and validation/output schemas describe their intentionally different shapes. Raw Python codes/members/reference objects and old JSON reference input fail.

### 3. Graph and diagram

Run migrated reference graph/JSON tests, dictionary payload tests, and scoped ordinary relation/legacy import controls. Verify [the graph contract](contracts/graph-and-diagrams.md).

Expected result: one ordinary association edge and retained field row with matching target/hint; exactly one enriched diagram fields item per host/field with preserved field_id/type/order/reference_qualname and the ordinary FK flag; no generated special reference edge or duplicate FK row; one diagram arrow with zero_many/one multiplicity and the dictionary card/type hint. Check two different fields to one dictionary, cross-domain slices, NoGraphEdge and the unchanged structural FK fallback. Historical-input controls still load legacy graphs.

### 4. Adversarial verification

Use a temporary copy or isolated process for each mutation; never rewrite the user's production source or index. Separately restore bare Enum acceptance, NoRelation acceptance, missing-marker acceptance, nonreciprocal acceptance and special-edge generation. Run the focused regression plus a valid neighboring control for each mutation.

Expected result: the targeted guarantee fails and the valid control passes. Record exact mutation, command and output. Restore/remove temporary state; check production files remain untouched by mutation.

### 5. Scoped closing checks

After auditing allowed roots/imports, expand to permitted package tests and apply changed-file lint/format checks. Candidate commands, with paths scoped explicitly:

```sh
.venv/bin/ruff check packages/aoa-action-machine/src packages/aoa-action-machine/tests packages/aoa-maxitor/src packages/aoa-maxitor/tests
.venv/bin/ruff format --check packages/aoa-action-machine/src packages/aoa-maxitor/src
```

Audit type-check dependency traversal and configuration before scoped mypy: the root configuration includes excluded package paths. Use a dedicated allowed-root configuration/input set if necessary and report it. Similarly audit wheel/sdist build dependencies and package smoke tests before invocation; do not use workspace aggregate commands.

For the permitted client, after dependency availability/import checks, the existing client-local checks are shown below. Direct execution of the TypeScript renderer script requires a Node runtime with TypeScript support or the repository's supported equivalent runner; verify that prerequisite without installing an unrequested runner:

```sh
npm --prefix packages/aoa-maxitor/client run build
node packages/aoa-maxitor/client/scripts/check-erd-dictionary-values.ts
```

Other client regression checks remain candidates if applicable and audited. Do not install/upgrade dependencies merely to hide a test failure. Report unavailable tool/dependency coverage.

### 6. Documentation and changelog

After the scoped closing run, execute all changed teaching scripts and corresponding notebooks in fresh environments, compare actual output and validate documentation blocks/local anchors. Number new scenarios after the existing sequence rather than overwriting unrelated topics. Document any direct-cell execution instead of a Jupyter kernel accurately. Then write the general article and behavior-package changelogs last.

## Completion evidence

Report commands and actual results, scope limits, example output, schema/graph/payload evidence, mutation outcomes and any reproduced source defects. Never call this a full repository check. No commits, staging, pushes, PRs or merges are authorized by this guide.
