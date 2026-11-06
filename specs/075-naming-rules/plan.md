# Implementation Plan: Every base class names its descendants

**Branch**: `feature/issue-486-naming-rules` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

`src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Design

- **One helper** — `src/naming/suffix.py` (new): `require_suffix(cls, base_name, suffix)` raises `NamingSuffixError(f"Class '{cls.__name__}' inherits {base_name} but lacks the '{suffix}' suffix. Rename to '{cls.__name__}{suffix}'.")`. The base classes that have no rule today call it from `__init_subclass__`; the existing rules (`Action`, `Domain`, `Role`, `Event`, entity kinds) keep their own wording.
- **Resource kinds** — `BaseResource.__init_subclass__` refuses a class whose direct bases include `BaseResource` unless it is one of the three kind bases (`DeclarationStructureError`). `BaseStorage`, `BaseGateway`, `BaseController` each check their descendants: the name ends with the kind, or with the kind and `Wrapper`; a name ending with `Wrapper` must end with `<Kind>Wrapper`. The model build (the coordinator's resource pass) checks every `get_wrapper_class()` target it can reach without an instance: the class each resource's wrapper class names, read from the resource's declared wrapper where it is a class attribute or from an instance-free call when the method does not use `self`; where neither is possible, the wrapper's own declaration already carries the kind rule.
- **Renames** — `resources/sql/sql_resource.py` → `sql_storage.py` (`SqlStorage`), `wrapper_sql_resource.py` → `sql_storage_wrapper.py`, `protocol_sql_resource.py` keeps its protocol (not a resource); `resources/postgres/postgres_resource.py` → `postgres_storage.py`; `plugin/core/plugin.py` keeps its module, the class becomes `BasePlugin`; `model/params_stub.py` and `result_stub.py` keep their modules, the classes become `StubParams`, `StubResult`. Package facades export the new names only.
- **The other packages** — `aoa-fastapi-adapter` `SocketChannel` → `SocketChannelController`; `aoa-langgraph` `WrapperLangGraphController` → `LangGraphControllerWrapper`; `aoa-ocel` resources on `BaseStorage` with storage names; the demo's resources take storage names (`StorefrontDatabase` → `StorefrontDatabaseStorage`, `IdentityStore` → `IdentityPostgresStorage`, `IdentityStoreBase` → `IdentityStorage`, `IdentityStoreStub` → `IdentityStubStorage`, and so on).
- **Tests, examples, notebooks, docs** — every resource double chooses a kind (a store of rows → storage, a call out → gateway, an object it owns → controller) and its name follows; about a hundred classes, renamed mechanically and checked by importing and running each.
- **`@on`** — `intents/on/on_decorator.py::_validate_method` refuses a name not starting with `on_`.
- **Graphs and versions** — the demo's graph is rebuilt (node ids carry class names); every changed package raises its version.

## Constitution Check

One phase = one commit; adversarial verification; the tail (check run, documentation, changelog); versions raised. Nothing outside AOA (gnomon) moves here.
