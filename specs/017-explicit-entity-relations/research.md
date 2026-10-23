# Research: where each of the six rules binds, and what it measures

**Feature**: `specs/017-explicit-entity-relations` | **Date**: 2026-10-23 | **Plan**: [plan.md](./plan.md)

Every decision below was taken against the merged baseline `2e70a30d` and confirmed with a runnable probe, not by reading the issue. The probes live in the plan's phases as tests; here are their answers.

## Measured baseline

| Measurement | Command | Result |
| --- | --- | --- |
| Bare structural-entity field | a model with `showcase: ShowcaseCoreEntity` | builds; `model_fields` is `['id', 'showcase']` |
| Mutable member | a `tuple[str, ...]` property whose after-validator returns `list(...)` | member published; `by_code("item").labels` is `['original', 'changed']` |
| Shape mismatch | a `tuple[str, ...]` property whose after-validator returns a joined `str` | published with a serializer warning; export is `{'labels': 'a'}` |
| Enum schema | a dictionary with a `Grade` property, `model_json_schema(mode="serialization")` | `KeyError '#/$defs/Grade'` |
| Relation default | `= Rel(description=…)` | `is_required()` is `False`; the omitted value is a `Rel` |
| `Classifier(field=…)` | grep over `packages/`, `examples/`, `docs/` | 165 occurrences in 53 files; 112 matches in 39 notebooks |
| `= Rel(description=…)` | the same grep | 262 declarations, 7 of them nullable; 44 notebooks |
| Python / Pydantic | `python -c` | 3.12.12 / 2.12.5 |

## D1 — The field refusal binds at the graph-build boundary

**Decision**: the new pass runs inside `NodeGraphCoordinator.build()`, immediately after `entity_specialization_validator.validate_entity_specializations()`, and is exposed as one module-level `validate_entity_fields()` so a test can call it directly.

**Rationale**: that method is the repository's existing definition of "a usable graph is published" — it already refuses a broken specialization after gathering nodes and before storing them. The classes are all loaded by then, forward references are resolved, and `declared_entity_classes()` already walks the `@entity` classes while skipping `exclude_graph_model` ones.

**Alternatives considered**: a metaclass hook at class creation (rejected — forward references and classes that never join a graph); a check in each resolver (rejected — eight containers and two intents would each need it); lazy on first `model_fields` read (rejected — too late to refuse a graph).

## D2 — Kinds are detected by the base classes, not by names

**Decision**: a resolved type is structural when it is a subclass of `BaseCoreEntity`, `BaseAssocEntity`, `BaseDetailEntity`, `BaseSpecEntity` or `BaseStateEntity`. `BaseEnumEntity` is a dictionary reference and `BaseSchema` descendants are not entities, so both are skipped before the walk.

**Rationale**: each kind has its own base and each base already enforces its naming suffix, so membership is a class relationship rather than a string test — the same stance the naming rule takes.

**Alternatives considered**: reading `entity_type` from a class attribute (rejected — it is computed for the declared-value kinds, not for every structural class); matching the `…CoreEntity` suffix (rejected — the suffix is a naming rule, and a rule must not be the type system).

## D3 — The walk reads resolved annotations and never evaluates strings

**Decision**: walk `cls.model_fields`; strip `Annotated` metadata; decide on the resolved type. For a forward reference, use what Pydantic resolved — measured:

```text
forward annotation: <class '__main__.TargetCoreEntity'>
```

**Rationale**: `model_fields[...].annotation` is already resolved when the class exists, so a field named through a string is judged by the class it names; nothing re-runs `get_type_hints` and no string is passed to `eval`. A field whose annotation never resolves fails the existing unresolved-name path, which is not the same as being declared a scalar.

**Alternatives considered**: `typing.get_type_hints(cls)` (rejected — executes module globals again and can raise for a name that is genuinely gone); judging the raw `__annotations__` string (rejected — that is exactly the "scalar evidence" the spec forbids).

## D4 — `NoRelation` mirrors the existing markers

**Decision**: `NoRelation(reason)` is a module-level frozen class in `relation_markers.py` with `__slots__`, refused assignment, `__eq__`/`__hash__`/`__repr__`, a nonblank `reason`, and its own AI-CORE block. It is exported from `aoa.action_machine.domain`.

**Rationale**: `NoInverse()` and `NoGraphEdge()` are the shape a marker takes in this repository — stateless, frozen, value-equal — and a third marker that behaves differently would be a second convention. The reason is the point of the marker, so it is required, not optional.

**Alternatives considered**: a boolean flag on `Inverse` (rejected — a relation and a refusal are mutually exclusive); reusing `NoGraphEdge()` (rejected — hiding an edge and declaring no relation are different statements, and the spec names the difference).

## D5 — `Classifier` loses the argument at construction time

**Decision**: `Classifier.__init__(variant)` only; the `_field` slot, its validation and the `marker.field != field_name` comparison are deleted. A stale `field=` keyword raises `TypeError` from the constructor.

**Rationale**: the refusal FR-035 asks for already exists as a Python error the moment an unknown keyword is passed — no new message, no new branch. The comparison the validator performed could only ever compare the attribute name with itself.

**Alternatives considered**: keep `field` as an ignored keyword (rejected — silent acceptance is exactly what the issue removes); keep it as a deprecation (rejected — it names a value that can never be wrong in a useful way).

## D6 — The card is projected in the payload action, and the tooltip follows an existing precedent

**Decision**: `list_entities_action.py` drops `code` and `display_name` from the payload's `fields` for `entity_kind == "enum"` only, and `buildDotSource.ts` puts `TOOLTIP="code: …"` on the value row's label cell.

**Rationale**: the stored graph carries the enum's fields, and the payload action is the only place that already reshapes a stored node for display. The tooltip is not a new mechanism: the specialization axis row already carries `TOOLTIP` for the alternatives it collapses, so the renderer gains no new concept.

**Alternatives considered**: deleting the rows when the graph is built (rejected — the graph is data, the card is presentation, and the graph schema keeps both); an HTML `<title>` element (rejected — Graphviz's `TOOLTIP` is the attribute this renderer already uses).

## D7 — The member check runs between construction and publication

**Decision**: in `declared_values.py`, each member is constructed as today, then verified before `cls.members` and `cls._by_code` are assigned. The verification compares each property's runtime value with its declared annotation recursively and applies the immutable set to it.

**Rationale**: `__pydantic_init_subclass__` already builds `members` in declaration order and publishes them in one assignment (measured: lines building `members` and `_by_code`); inserting the check between construction and that assignment is the only position where a refused member was never reachable. Comparing the runtime type with the annotation is what catches the shape mismatch, which the baseline exports with a warning only.

**Alternatives considered**: checking inside `to_reference()` (rejected — every reader would pay, and the invalid member would still be published); freezing instead of refusing (rejected by FR-011 and by the spec's explicit "do not silently freeze").

## D8 — An `Enum`'s own value is part of the contract

**Decision**: when a property's annotation is an `Enum` subclass, the declared member's value is checked with the same immutable set and the same recursion.

**Rationale**: measured — `class Flags(Enum): X = ["a", "b"]` passes declaration, and `Flags.X.value.append("c")` changes what `by_code("item").to_reference()` returns for every consumer. Accepting the annotation alone is the same mistake the annotation-only hook already makes.

**Alternatives considered**: accepting any enum value because members are singletons (rejected — a singleton whose value is a list is a shared mutable list); refusing enums entirely (rejected — an `Enum` is an explicitly supported annotation and #244 already ships it).

## D9 — Definitions survive by keeping what the generator produced

**Decision**: `_emitted_reference_schema()` keeps the `$defs` of the generated document, copies only the definitions actually referenced by the emitted property fragments (transitively), and derives the nested `properties.required` from the generated `required` list instead of omitting it.

**Rationale**: measured — the generated document at the point the current code projects from already contains everything needed:

```text
top keys: ['$defs', 'additionalProperties', 'description', 'properties', 'required', 'title', 'type']
$defs: ['Grade']
properties: ['code', 'display_name', 'grade']
required: ['code', 'display_name', 'grade']
grade fragment: {'$ref': '#/$defs/Grade'}
```

The defect is not in generation but in the projection, which copies `properties` and drops the rest. Keeping the referenced definitions is smaller than generating each property separately, and it keeps serializers' output shapes, because the document is generated in serialization mode.

**Alternatives considered**: flattening every property into an untyped object (rejected explicitly by FR-016); inlining `$ref` targets (rejected — it loses shared definitions and collides on the same short class name, the case FR-020 requires); resolving definitions by name after generation (rejected — a name-based lookup breaks on two classes with the same short name).

## D10 — The relation default is judged from `FieldInfo`, never from a value

**Decision**: for every field inside a relation container, the check reads `field_info.is_required()`, `field_info.default` and `field_info.default_factory` and refuses: any default other than an explicitly permitted `None`, a `None` default on a non-nullable annotation, and any factory. The description is `field_info.description`, which must be a nonblank string. Both intent resolvers read that one attribute.

**Rationale**: Pydantic has already merged both supported syntaxes into one `FieldInfo` — measured:

```text
inner+outer: OUTER True     # Annotated Field + assigned Field
inner only:  INNER True     # Annotated Field alone
```

so the rule needs one attribute and no annotation parsing, and a factory is refused without being called because `default_factory` is read, not invoked. The baseline's own probe showed the failure the rule prevents:

```text
Rel required: False    Field required: True    Omitted value type: Rel
```

**Alternatives considered**: enabling Pydantic's `validate_default` (rejected by FR-032 — it validates the leaked value instead of refusing the declaration); executing a factory to inspect its result (rejected — user code would run during validation); reading the description from a default object when present (rejected — the source of the two `_field_description_hint()` copies).

## D11 — The migration counts are refreshed, not trusted

**Decision**: each migration phase opens by re-running the same grep that produced its baseline count, and records the new number in the phase's task.

**Rationale**: the counts were measured on `2e70a30d` and the corpus moves between issues — the issue's own `Classifier` figure (162 in 51 files) already differs from the measurement here (165 in 53 files). A migration planned on a stale count leaves a file behind and the phase fails its own exit test.

**Alternatives considered**: trusting the issue's inventory (rejected — it is explicitly labelled as a baseline); migrating by search-and-replace only (rejected — `Rel` and `Classifier` both appear inside docstrings and prose that must read naturally afterwards).

## Open items carried into implementation

- The exact wording of the four refusals is decided while writing them, and each is asserted by a test that names the owner and the field.
- `properties.required` for an intentionally excluded field is decided by the emitted document, not by a field list — the test derives the expectation from the export.
- The tooltip text is `code: <code>`, matching the vocabulary the payload uses; a dictionary whose code needs escaping is covered by the existing escaping rule.
