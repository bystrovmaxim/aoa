# Research: Complete Annotated Relationships

**Date**: 2026-10-24
**Status**: Planning research complete; findings describe current code, not implemented feature behavior.

## R1 — Canonical declaration metadata

**Decision**: Normalize completed Pydantic field annotations and metadata once; validate/resolve/project from that view.

**Evidence**: `intents/entity/entity_relation_intent_resolver.py` re-runs `get_type_hints(include_extras=True)`, falls back to `field_info.annotation`, and reads direction markers only from the recovered annotation. A caller's explicit `model_rebuild` namespace may resolve Pydantic fields while the original module globals still cannot resolve the hint. The fallback therefore loses metadata. Its first-marker/first-union-member behavior also obscures conflicts.

A local Pydantic 2.12.5 probe reported:

```text
a annotation= aoa.action_machine.domain.relation_containers.AssociationOne[str] markers= ['NoInverse'] description= Assigned
b annotation= aoa.action_machine.domain.relation_containers.AssociationOne[str] markers= ['NoInverse'] description= Inline
```

Both assignment-side and annotation-side Field settings become normalized field data. Runtime code cannot honestly prove the original source placement/count from that view. Enforce semantic completeness at runtime and source spelling through an explicit-root AST check.

**Alternatives rejected**: Re-evaluating strings against guessed globals; treating metadata absence as implicit NoInverse; accepting whichever union member happens to come first; requiring source files for production model validation.

## R2 — Completeness and inverse boundary

**Decision**: Separate all-declared-host completeness enumeration from graph publication enumeration. Add build-local reciprocal endpoint validation without a new compatibility matrix.

**Evidence**: `graph/validators/entity_field_validator.py` accepts bare Enum/NoRelation, rejects wrapped Enum and does not count direction markers. It uses `declared_entity_classes()` from the specialization validator, which omits excluded classes. `NodeGraphCoordinator.build()` runs field validation before node gathering. The factory and ActionProductMachine/TestBench call this build path; direct `EntityGraphNode` construction currently bypasses it. Ordinary inverse reciprocity is not implemented by the inspected resolver/graph path.

**Rationale**: A graph-hidden host must not bypass the declared contract. A graph constructor must not recurse through reciprocal graph construction just to check a pair; inspect resolved endpoint descriptors instead. Preserve specialization enumeration and classifier logic, adapting only the agreed completeness/reciprocity behavior.

**Alternatives rejected**: Removing exclusion globally from specialization gathering; a new global entity registry; constructor recursion through inverse nodes; restoring one-sided pairing; adding the rejected ownership matrix.

## R3 — Dictionary generic schema handling

**Decision**: Add Pydantic handling scoped to the resolved dictionary target of AssociationOne; leave structural wrapper semantics unchanged.

**Evidence**: `domain/relation_containers.py` defines plain frozen generics with no schema hooks. `model/base_schema.py` enables arbitrary types. An isolated probe with a concrete dictionary and a plain Pydantic host observed:

```text
canonical lookup: True
container host: AssociationOne(id='eu', id_only) entity: None
json output PydanticSerializationError Unable to serialize unknown type: <class 'aoa.action_machine.domain.relation_containers.AssociationOne'>
validation schema PydanticInvalidForJsonSchema Cannot generate a JsonSchema for core_schema.IsInstanceSchema (<class 'aoa.action_machine.domain.relation_containers.AssociationOne'>)
serialization schema PydanticInvalidForJsonSchema Cannot generate a JsonSchema for core_schema.IsInstanceSchema (<class 'aoa.action_machine.domain.relation_containers.AssociationOne'>)
```

The wrapper also allowed a fabricated member to remain inside a host. Raw code/reference inputs already fail instance validation, but hydration/canonical validation and export/schema generation require work.

`domain/enum_entity.py` already enforces canonical member identity and implements separate input/output schemas and JSON reference serialization. `domain/declared_values.py::by_code` raises KeyError for missing codes; normalize that into a validation error at the host-field boundary. Reuse handler-managed dictionary definitions and property serializer effects. A raw dictionary core schema must not become a shortcut that accepts a bare reference as a relationship.

**Input design**: Python requires an explicit wrapper; JSON supplies an explicit `{id: code}` container object. This is the transport form of a wrapper, not a bare code/reference. Additional JSON keys are refused. The validated result is a new wrapper with canonical entity identity. Python dictionary mappings are not an additional implicit conversion path.

**Alternatives rejected**: Mutating frozen input wrappers; accepting canonical members as bare field input; equality instead of identity; globally changing all structural relationship hydration; copying schema definitions by hand.

## R4 — Ordinary association projection with retained dictionary row

**Decision**: Route new dictionary relationships only through the existing ordinary relation projection. Retain their field rows and hints. Keep historical special-edge import support.

**Evidence**: `graph/edges/entity_graph_edge.py` already emits all required ordinary association properties and honors NoGraphEdge. `EntityGraphNode` currently separately gathers special dictionary references. `EntityFieldGraphEdge.get_entity_field_edges()` excludes ordinary relation names wholesale; it needs a targeted retained-row rule for dictionary associations. `nodes/entity_field_graph_node.py::declared_dictionary` currently unwraps only Annotated/optional, not AssociationOne.

Maxitor's `list_entities_action.py` ordinary relation query already emits association with host/dictionary multiplicities zero_many/one. The legacy reference branch emits reference with a different orientation. `duckdb_graph_resource.py` stores both kinds, so preserve its historical import support while migrating new fixtures and consumer expectations.

**Alternatives rejected**: Keeping special new edges contrary to clarification A; generating both kinds; deleting historical schema/loader support; retaining metadata while accidentally dropping the field row.

## R5 — Verification scope and corpus migration

**Decision**: Audit and migrate only permitted roots; use isolated invalid-declaration fixtures. Keep the same physical branch as the user created.

**Evidence**: The project-wide check script includes prohibited package work and broad auto-fixes. It cannot be used in this task. Test conftest modules under the selected action-machine tree use its own support model. Package tests share module names, so explicit importlib mode avoids cross-package import collisions.

Current focused baseline command selected relation containers, markers, field validator, reference graph, dictionary-reference JSON and Maxitor dictionary payload tests. Actual result:

```text
107 passed in 0.90s
```

This is baseline evidence only; these tests currently encode behavior that must change. No claim is made that the new guarantees pass.

Local versions: Python 3.12.12, Pydantic 2.12.5, pydantic-core 2.41.5, pytest 8.4.2, DuckDB 1.5.2. No dependency upgrade is required for the design.

**Alternatives rejected**: Running all workspace commands and hoping exclusions apply; modifying prohibited fixtures to get green; treating graph-excluded invalid fixtures as harmless after completeness begins inspecting them; creating another branch or commit as a planning side effect.

## R6 — Feature gates and documentation

**Decision**: Replace the obsolete checklist demand for a new pair matrix with a check that the clarified scope excludes it and preserves existing rules. Reserve the three required closing tasks explicitly.

**Rationale**: An unchecked requirement that the maintainer removed is not an unresolved feature decision. The checklist must review the current specification, not the superseded draft. English artifact links and scoped check limits follow the current explicit instructions.

**Alternatives rejected**: Treating the removed matrix as implementation debt; retaining contradictory checklist notes; silently claiming a full repository pass or complete future execution.

## R7 — Analysis remediation: inherited inverse endpoints

**Decision**: Separate effective_host from declaring_owner and validate reciprocal canonical declaring endpoints. Unchanged inheritance preserves its base pair; explicit or target-changing semantic overrides create new endpoints. Resolve multiple inheritance by normal model/MRO selection and keep per-effective-host graph projection.

**Rationale**: Comparing an unchanged inherited field against the child class identity alone would reject a valid reverse field still targeting the base. A blanket subclass allowance would instead hide unrelated/overridden endpoint errors. Both are avoided by declaration provenance and explicit canonical endpoint resolution. The declaration contract provides the complete acceptance table.

**Alternatives rejected**: Requiring every unchanged subclass to duplicate reverse fields; auto-retargeting base pairs; ignoring all inherited fields; matching targets by issubclass or short names.

## R8 — Analysis remediation: one enriched diagram field row

**Decision**: Enrich the retained dictionary field row with matching ordinary FK metadata and suppress its synthesized fallback by host/field identity, preserving the row's field_id/type/order/reference_qualname.

**Evidence**: Current Maxitor SQL emits ordinary FK rows and retained field rows through UNION ALL, then applies full-row DISTINCT. Their different field_id/type/ordinal values prevent that DISTINCT from merging the proposed dictionary association's two representations.

**Alternatives rejected**: Allowing two visible rows for one field; discarding the retained hint/field identity; collapsing two different fields by dictionary target; changing historical reference or ordinary structural fallback behavior.

## R9 — Pre-change compatibility evidence

**Decision**: Capture selected existing compatibility/classifier inputs and actual outcomes before production changes in T002, and consume that immutable evidence in T032. The baseline command selects six files; its 107-test result is not a complete compatibility baseline.

**Rationale**: Expected outcomes derived only after changing the implementation cannot demonstrate preservation of the former behavior. No new pair matrix is inferred from the added evidence.

## Design review result

Initial read-only design reviews found no material contradiction in the reviewed paths. The subsequent cross-artifact analysis identified inherited endpoint provenance and diagram-row merging as underspecified; R7/R8 and the corresponding contracts/tasks now resolve those design gaps. This supersedes any broader reading of the initial review result. The Python-wrapper versus JSON-container input distinction needs explicit paired acceptance tests. Direct execution of client TypeScript scripts requires a compatible Node runtime; the validation guide records this prerequisite.

All planning artifacts passed structural/link checks. The requirements-quality checklist is reconciled to the clarified scope and the analysis remediation items. These reviews certify the design, not future implementation or acceptance-test results.
