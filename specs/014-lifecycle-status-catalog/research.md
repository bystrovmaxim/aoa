# Research: Lifecycle statuses on the state type

**Feature**: `specs/014-lifecycle-status-catalog` | **Date**: 2026-10-22 | **Plan**: [plan.md](./plan.md)

The clarifications in the specification settle the scope. This file records the technical decisions behind the plan, the alternatives that were measured, and the evidence the design rests on. Every "measured" number was taken on `main` after #210 (PR #238).

## D1. The surface: the class name, an internal factory, and a Pydantic hook

**Decision**: inside a state type body the type's own name resolves to an internal `state(**kwargs)` factory. `state` returns a `StateSpec` placeholder. `BaseStateEntity.model_config` lists `StateSpec` in `ignored_types`, so Pydantic does not treat the placeholder as a field. `BaseStateEntity.__pydantic_init_subclass__` scans `cls.__dict__` for placeholders, replaces each with `cls(**spec.kwargs)`, and fills the catalogue.

**Rationale**: the model author writes `DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)` — the simplest possible surface, typed by mypy as `OrderStateEntity`, with no `cast`, no `state(...)`, no `TYPE_CHECKING`. The status lines move unchanged from today's axis to the type, which makes the 55-axis migration mechanical. The conversion runs after the model is built, so `cls(**kwargs)` is the ordinary Pydantic constructor: required fields, defaults, types and `extra="forbid"` are checked there, at class creation.

**Evidence**: a prototype against the current `BaseStateEntity` and `Lifecycle` produced `members == ['draft', 'paid', 'cancelled']`, a full `model_dump()` for every status, `ValidationError: Extra inputs are not permitted` for `sort_ordr=99`, `ValidationError: Field required` for a missing `code`, and `int` coercion for `sort_order="42"`.

**Alternatives considered**:

- **A metaclass that creates the instances after `type.__new__`.** Workable and prototyped, but the metaclass then owns the conversion; the hook is the narrower, documented Pydantic seam.
- **A public `state(...)` factory.** No metaclass, but the surface changes to a framework-specific call and needs `cast`/`TYPE_CHECKING` to keep the field types; more concepts for the AI and a rewriting step in the migration.
- **Explicit assignment after the class.** `DRAFT: ClassVar["OrderStateEntity"] = ...` below the class; typing is perfect and there is no hook, but the statuses leave the body, each status costs two lines, and the surface is not the issue's.
- **A nested status type in the axis.** Works today with no framework change, but the catalogue stays on the axis and the role split — the point of the feature — does not happen.
- **A descriptor whose `__set_name__` creates the instance.** Runs even earlier than the hook, during `type.__new__`, and cannot rely on the finished model.

## D2. The alias is the only special rule

**Decision**: `StateEntityMeta.__prepare__` returns a dict subclass whose missing-name lookup answers the class's own name with `state`. No slot is created, no instance is built, and the metaclass has no other role. Every other unknown name still raises `NameError`.

**Rationale**: Python does not bind the class name while its body runs; the class namespace is the only place to intercept it. The alias is documented as "in a state type body, the type's own name is the declaration factory", which is a rule an author can state in one sentence.

**Cost accepted**: a global with the same name as the state type is shadowed inside its body. A test pins it, and the reference page names it. A field annotation referring to the type itself must stay a forward reference (the alias is a call form, not the class).

## D3. The generic axis and the type's origin

**Decision**: `Lifecycle` becomes `Generic[StateT]` with `StateT` bound to `BaseStateEntity`. `Lifecycle.__init_subclass__` reads the type from `cls.__dict__.get("__orig_bases__")` via `get_origin`/`get_args`, stores it as `_state_type`, and lets a subclass inherit the stored type when it has no generic base of its own. A plain `Lifecycle` subclass has no parameter and is not checked.

**Rationale**: the axis must name the type once, and the refusals need the catalogue. `__orig_bases__` is the standard place a generic base leaves its arguments; the runtime class is unchanged, so `OrderLifecycle(current_state="draft")` and the entity field keep working.

**Cost measured**: 22 `Lifecycle` annotation lines across 9 files (the scan includes docstring mentions; mypy confirms the exact set) become `Lifecycle[BaseStateEntity]` or `Lifecycle[Any]`; `disallow_any_generics` makes every bare annotation an error. The `state_vocabulary.py` site disappears with the module. No new `# type: ignore` is allowed.

**Alternatives considered**:

- **Class keyword `class X(Lifecycle, state_type=Type)`.** Same checks, no `Generic`, no `disallow_any_generics` sweep; rejected in clarify in favour of the issue's form.
- **A separate `TypedLifecycle` base.** Keeps `Lifecycle` unchanged but leaves two axis bases; rejected.
- **An explicit `_state_type = Type` attribute on the axis.** Works, but it is a second declaration next to the base and drifts from the type; rejected.

## D4. The two refusals

**Decision**:

- **Foreign**: every entity in `template.get_state_entities()` and `template.get_transition_entities()` must be one of `state_type.members` by identity. If the code is not declared, `ForeignStateError` names the axis, the code, the type and the allowed codes. If the code is declared but the object is not the member, the message says it is a different instance and names the attribute to use (`OrderStateEntity.DRAFT`), resolved through the MRO.
- **Missing**: every member must appear in `get_state_entities()`, never in the targets only. `MissingStateError` names the axis, the type and the missing codes.
- **Empty catalogue**: an axis over a state type with no members and a template with states raises `ForeignStateError` saying the state type declares no statuses — the statuses cannot be members of an empty catalogue.

Both run in `Lifecycle.__init_subclass__`, at class creation, before any graph is built.

**Rationale**: the current check is `entity not in declared`, which compares Pydantic fields; an equal twin passes and the template holds an object the catalogue does not expose. Identity is the guarantee the contract states. Coverage is the missing half: a declared status the axis never uses is silent today.

**Alternatives considered**:

- `isinstance` for the foreign check: accepts an undeclared instance of the right type; rejected.
- `==` (the current check): the defect; rejected.
- Coverage including transition targets: a target is not a state; `.to(CANCELLED)` must not satisfy the coverage rule; rejected.
- A subset opt-out: the clarify settled that every status is mandatory and a narrowed axis declares its own type; rejected.

## D5. The catalogue lives on the state type

**Decision**: `members: ClassVar[tuple[BaseStateEntity, ...]]`, `codes()`, `by_code(code)` (raises `KeyError`) and `entity_type` (the type itself) live on `BaseStateEntity`. A subclass with no placeholders inherits `members`; a subclass that declares placeholders gets its own tuple; a type with no statuses keeps an empty tuple.

**Rationale**: the statuses belong to the type; the axis is the machine. The API is the same shape the axis had, so the call sites move one level down.

**Measured call sites**: 13 lines in tests and examples read `by_code`, `codes()`, `members` or `entity_type` on an axis; the migration moves them to the state type.

## D6. `StateVocabulary` is removed

**Decision**: `domain/state_vocabulary.py` is deleted; `StateVocabulary` leaves `domain/__init__.py`; no alias and no deprecation release.

**Rationale**: the mixin's three jobs split — collection and duplicate codes to the hook, the template check to `Lifecycle.__init_subclass__`, the lookup API to the state type. Keeping the mixin would leave two grammars for one declaration, and the clarify chose one.

**Measured surface**: 110 `StateVocabulary` mentions across Python (55 live class declarations, imports, docstrings); 12 in the framework's tests; the docs and the examples mention it too. The codemod and the scan take the Python count to zero; the docs phase rewrites the prose.

## D7. The hook runs after the model, not before

**Decision**: the conversion is `__pydantic_init_subclass__`, not `__init_subclass__`.

**Rationale**: `__init_subclass__` runs while Pydantic is still building the class; a prototype showed `model_fields == []` and `cls(x=1)` created a fieldless instance there. `__pydantic_init_subclass__` runs after `model_fields` are set, and the same call validates every field. The existing `__init_subclass__` (name suffix, `exclude_graph_model`) is untouched and runs first.

**Cost accepted**: the conversion is one Pydantic-specific hook; the docs name it, and the plan's tests assert the ordering by checking that a misspelled field fails at class creation.

## D8. The placeholder is excluded from model fields

**Decision**: `BaseStateEntity.model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(StateSpec,))`.

**Rationale**: without the entry, Pydantic raises `PydanticUserError: A non-annotated attribute was detected` for every `DRAFT = StateSpec(...)`. With it, the placeholder stays a class attribute until the hook replaces it.

**Cost accepted**: a subclass that overrides `model_config` must preserve `ignored_types`; a test covers the override, and removing the entry is one of the adversarial breaks.

## D9. The migration is mechanical, with a baseline

**Decision**: an AST codemod moves every status assignment from the axis to the state type (the type is the first argument of the call), removes `StateVocabulary` from the bases, parameterises the axis with the type, and qualifies the bare names in `_template`. A scan and a baseline are taken before and after; the comparison is the evidence that no status, label, transition or field moved.

**Rationale**: 55 axes and 64 state types are too many for hand edits; the surface is unchanged, so the move is textual. The baseline covers the demo's graph state rows and the entity field types (SC-005); the scan reports 0 axes on `StateVocabulary` and 0 uncovered statuses after.

**Measured corpus**: 55 axes (32 demo, 16 examples, 7 framework tests); 64 state types (32 demo, 24 examples, 8 framework tests); every demo axis already uses every declared status, so the coverage rule adds no status.

## D10. Typing

**Decision**: model code has no `cast` and no `TYPE_CHECKING`; `DRAFT` is typed as the state type because the surface is a call to the class. `state(...)` arguments are validated by Pydantic at class creation, not by mypy; the `pydantic.mypy` plugin would check them statically and is out of scope. All bare `Lifecycle` annotations are parameterised; no new `# type: ignore`.

**Rationale**: mypy resolves the self-reference in the class body to the class being defined, so the attribute type is exact; the runtime alias does not affect static analysis. The generic sweep is the price of the chosen form and is measured at 22 annotation lines.

## D11. Plain `Lifecycle` stays

**Decision**: a `class PlainLifecycle(Lifecycle)` with a `_template` keeps today's behaviour and is not checked.

**Rationale**: not every lifecycle needs a catalogue; the escape is one test and keeps the change from forcing a type on every axis.

## D12. Cases the documentation must show

**Decision**: the documentation phase ships `20_missing_status`, `21_twin_instance`, `22_status_fields` and `23_plain_lifecycle` as script and notebook beside the existing lifecycle cases, and updates the foreign-status case. Each case is executed while written (constitution VI.5).

**Rationale**: the feature's value is in what is refused and in what is initialised; a reader who does not see the twin refusal, the missing status and the field errors will get them wrong. The reference page states the alias's shadowing cost and the plain-`Lifecycle` escape.

## Evidence files

- `evidence/scan_lifecycle_catalog.py` — counts, coverage, per-axis/per-type dump, before and after.
- `evidence/baseline.before.json` / `baseline.after.json` — axes, statuses, labels, template states and transitions, the demo's graph state rows and entity field types.
- `evidence/compare_baselines.py` — the per-axis diff; a deliberate break proves it fails.
- `evidence/migrate_lifecycle_catalog.py` — the AST codemod; refuses on a collision and prints a per-file change count.
