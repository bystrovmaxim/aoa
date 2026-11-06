# Implementation Plan: Every base class names its descendants

**Branch**: `feature/issue-486-naming-rules` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

`src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Design

- **One helper** — `src/naming/suffix.py` (new): `require_suffix(cls, base_name, suffix)` raises `NamingSuffixError(f"Class '{cls.__name__}' inherits {base_name} but lacks the '{suffix}' suffix. Rename to '{cls.__name__}{suffix}'.")`. The base classes that have no rule today call it from `__init_subclass__`; the existing rules (`Action`, `Domain`, `Role`, `Event`, entity kinds) keep their own wording.
- **Resource kinds** — `BaseResource.__init_subclass__` admits only the three framework kind bases as direct descendants, identified by their canonical declarations rather than a copied short name or a user-set attribute. Determine kind from their ancestry; never trust a descendant's `RESOURCE_KIND`. Reject mixed-kind ancestry with `DeclarationStructureError`; check the kind suffix or `<Kind>Wrapper` suffix for every descendant. Same-kind multiple inheritance follows Python's MRO.
- **Wrapper contract** — migrate `BaseResource.get_wrapper_class` and all overrides to `@classmethod def get_wrapper_class(cls)`. At model build, validate the inherited descriptor is a class method before calling it. Do not construct resources, pass a fake `self`, inspect method source or skip inaccessible targets. Visit every declared resource and recursively each wrapper result, using a visited set to terminate cycles. Accept `None`; require all other results to be resource classes of the original kind with `<Kind>Wrapper` suffix. Invalid descriptor, result type or kind raises `DeclarationStructureError`; a missing suffix raises `NamingSuffixError`. Getter exceptions fail the build and are not suppressed. Runtime nesting calls the same class-method contract; it does not substitute for build validation.
- **Renames** — `resources/sql/sql_resource.py` → `sql_storage.py` (`SqlStorage`), `wrapper_sql_resource.py` → `sql_storage_wrapper.py`, `protocol_sql_resource.py` keeps its protocol (not a resource); `resources/postgres/postgres_resource.py` → `postgres_storage.py`; `plugin/core/plugin.py` → `base_plugin.py` (`BasePlugin`); `model/params_stub.py` → `stub_params.py` (`StubParams`); `model/result_stub.py` → `stub_result.py` (`StubResult`). Other modules named after a renamed single class follow that class too; update direct imports and package facades together. Package facades export the new names only.
- **The other packages** — `aoa-fastapi-adapter` `SocketChannel` → `SocketChannelController`; `aoa-langgraph` `WrapperLangGraphController` → `LangGraphControllerWrapper`; `aoa-ocel` resources on `BaseStorage` with storage names; the demo's resources take storage names (`StorefrontDatabase` → `StorefrontDatabaseStorage`, `IdentityStore` → `IdentityPostgresStorage`, `IdentityStoreBase` → `IdentityStorage`, `IdentityStoreStub` → `IdentityStubStorage`, and so on).
- **Tests, examples, notebooks, docs** — every resource double chooses a kind (a store of rows → storage, a call out → gateway, an object it owns → controller) and its name follows; about a hundred classes, renamed mechanically and checked by importing and running each.
- **Scope exclusion** — `@on`, its `on_` prefix validation and `NamingPrefixError` are unchanged. T006 is withdrawn; the shared class-suffix helper is not applied to handlers.
- **Graphs and versions** — the demo's graph is rebuilt (node ids carry class names); every changed package raises its version.

## Verification and documentation

Each implementation phase runs only its own changed test files. For each new rule, remove or bypass the check deliberately, confirm the corresponding test fails and no unrelated test in that phase does, then restore the code. Record the command, exact output and restoration. Do not rerun a successful check without a subsequent change or unresolved concern.

T009 supplies paired runnable scripts and notebooks for: every governed base's accepted and rejected name; direct resource inheritance and attempted kind spoofing; mixed-kind refusal and same-kind inheritance; wrapper suffix checks, class-method inheritance, `None`, recursive wrappers and cycles; invalid descriptors, result types and kinds; getter exceptions; and public import migration. Cases may share a script/notebook pair, but each is named and its exact output explained. Existing examples are migrated as their code changes; new explanatory documentation is written after T008. Documentation execution is part of authoring, and CI executes it again as required by the constitution.

Old identifiers remain only in the specification, historical changelogs and labelled migration explanations. Before-migration snippets are explicitly non-runnable fragments. Active examples and imports use the new names and class-method contract.

## Constitution Check

One phase = one commit; adversarial verification; the tail (check run, documentation, changelog); versions raised. Nothing outside AOA (gnomon) moves here.

T008 takes every locally runnable closing check to zero, including `graph-builder check`, recording prior phase results without unnecessary repetition. T009 writes and executes documentation, then T010 writes one plain-language changelog article. Only after all three may a complete PR be opened on explicit instruction; its CI closing run must pass before a separately authorized merge. One phase is one commit, and commits require explicit authorization. The constitution itself is unchanged.
