# Research: Typed events, `@emits` and the domain vocabulary

Everything here was checked against `main` at b83eed70. Results marked "run" come from running real code; the scratch prototypes are not part of the repository.

## R1. Where `BaseEvent` lives, and how a domain recognises it

**Decision**: `model/base_event.py`, next to `BaseParams` and `BaseResult`, imported from that module and not exported from `model/__init__.py`, as `BaseState` is already imported in the examples. A new leaf module, `domain/event_marker.py`, holds `EventMarker`, a class with no content. `BaseEvent` inherits it, and `BaseDomain` imports it to validate `events`.

**Rationale**: `BaseEvent` needs `BaseDomain` and the log payloads for its system fields, and `BaseDomain` needs to recognise an event class when a domain is defined. Importing `BaseEvent` from `base_domain.py` is a cycle, because `aoa.action_machine.logging` itself imports `BaseDomain`. The marker breaks it with no import inside a function.

`model/__init__.py` must not reach `base_event.py` either. `context/request_info.py` imports the `model` package, and `base_event.py` imports `logging`, whose `console_logger.py` needs `Context`. Exporting `BaseEvent` from the package fails with `ImportError: cannot import name 'Context' from partially initialized module` whenever `context` is imported first.

Run: a prototype imported cleanly with each of fifteen modules imported first in a fresh process, including `context.context`, `context`, `auth`, `model`, `domain`, `logging`, `runtime.tools_box`, `runtime.action_product_machine`, `intents.emits` and `testing.bench`. A test states this rule, so an export added later fails at once.

**Alternatives considered**:
- An import inside `_validate_events`: works, but needs `# pylint: disable=import-outside-toplevel`, and production code carries nothing that exists only for a linter.
- Untyped system fields, so `base_event.py` imports nothing from `logging`: gives up the type of the very fields this work declares.
- Validating `events` only in the build check: a wrong `events` must fail when the domain is defined (FR-018).

## R2. How names are refused

**Decision**: `BaseEvent.__init_subclass__` checks the suffix and the field names, reading the subclass's own annotations with `inspect.get_annotations`.

**Rationale**: `__init_subclass__` runs before pydantic collects the fields, so a field named `get` is refused before pydantic warns that it shadows a method. It is the same hook `BaseDomain` and `BaseEntity` use.

Run on Python 3.12 and 3.14 with warnings turned into errors: the suffix, a system name, `get` and `items` were each refused, and no warning came first.

Run, why the five names are refused: with a field `get`, `var.get("level")` raises `TypeError: 'str' object is not callable`; `keys` breaks `{**var}` the same way. `values`, `items` and `resolve` shadow the methods of the same name.

## R3. How the author is kept away from the system fields

**Decision**: a `model_validator(mode="before")` on `BaseEvent` refuses a system name in the input. `box` fills them with `model_copy(update=...)`, which does not validate. The fields carry `Field(default=None, exclude=True)`.

**Rationale**: the check sees the name even when the value is `None`, and a copy leaves the author's instance untouched.

Run: `OrderEvent(order_id="o", level=None)` gives `ValidationError`; after `model_copy`, the copy holds the value, the source stays `None`, and `model_dump()` gives `{'order_id': 'o'}`.

## R4. The shape of the call

**Decision**: `async def info(self, channels, message, event=None, /, **kwargs)`, and the same for `warning` and `critical`, on `ToolsBox` only.

**Rationale**: the positional-only marker keeps a keyword named `event=` an ordinary `kwargs` variable. No call in `packages/` or `examples/` passes `channels=` or `message=` by keyword, so nothing breaks.

Run: `info(1, "t", event=5)` gives `(None, {'event': 5})`; `info(1, "t", 7)` gives `(7, {})`.

## R5. Where the rule is checked

**Decision**: inside `ToolsBox`, before anything reaches the logger, through an `EmissionRules` object passed to its constructor. `ToolsBox` gains no public method.

**Rationale**: plugins and the machine write through `ScopedLogger` directly and never through a `box`, so a check in `ToolsBox` covers operation code and only that (FR-016). A check in `ScopedLogger` or `LogCoordinator` would catch all three.

**Alternatives considered**: a check in `method_box` alone: `TestBench` builds its own box in `run_aspect`, `run_summary` and `run_compensator`, so the rule would pass there and fail in production. The three places pass the same object instead. `@on_error` and `@access_decide` reach `TestBench` only through a full run, so they already go through `method_box`.

## R6. How a method's declaration is read

**Decision**: `@emits` writes `_emits_events` on the function, as `@context_requires` writes `_required_context_keys`. `emission_rules_for(action_cls, method_name)` reads it with `getattr(action_cls, method_name)`, and reads the domain with the existing `resolve_domain`. It returns `None` when neither switch is on, so a run with no switch has no check to perform.

**Rationale**: all five decorators return the function unchanged, so the attribute survives whichever is applied first. #334 reads the same attribute to build the graph.

## R7. How `@emits` is refused on a wrong method

**Decision**: `@emits` validates its own arguments when applied. `BaseAction.__init_subclass__` then looks at the methods in the class body and refuses one with `_emits_events` that carries none of the four markers of an emitting method. The names of those markers and of `_emits_events` live in a leaf module, `model/emitting_method_markers.py`.

**Rationale**: `@emits` may run before the method's own decorator, so only the finished class can tell. `BaseAction.__init_subclass__` already exists. The names stay out of the `intents/emits` package, because importing any module of a package runs its `__init__.py`, which reaches `emits_decorator.py` and `BaseEvent`, and that is the cycle of R1.

## R8. The build check

**Decision**: a new validator, `graph/validators/emits_vocabulary_validator.py`, called from `NodeGraphCoordinator.build` once the nodes are wired. For each action node whose domain declares `events`, it walks the regular aspects, the summary aspect, the compensators, the error handlers and the access decision.

**Rationale**: it follows the four existing validators, and the action node already lists its methods. It changes no node and no edge, so the graph is untouched.

## R9. The declared type of `var`

**Decision**: `type LogVar = Any` in `logging/log_var_payloads.py`, used for `var` throughout the logging package.

**Rationale**: `dict[str, Any] | BaseEvent` makes mypy refuse every subclass declaring `var: dict[str, Any]`, and `mypy packages/` covers tests, so `ConsoleLogger` and five test files would have to change.

Run: `--strict` gives `[override]` for the union, and no issues for the alias, with subclasses declaring `dict[str, Any]` and `LogVar` both.

## R10. The refusal

**Decision**: one error, `EventContractError(TypeError)` in `exceptions/`, for a refused emission, a call with an event and `kwargs`, an object in the event's place, reserved field names, invalid `events`, and the build check. Suffix errors stay `NamingSuffixError`, and `@emits` keeps the decorator errors the other decorators raise.

**Rationale**: it is an ordinary exception, so it takes each method's ordinary path with no new code (FR-015). `CacheContractError(TypeError)` is the precedent.

## R11. `aoa-demo`

**Decision**: `fastapi_mcp_services/events.py` holds `OrderRequestedEvent(order_id: str)` and `OrderValidatedEvent(user_id: str, amount: float)`. `OrdersDomain.events` lists both. The two templates stay as they are, since they already read `{%var.order_id}`, `{%var.user_id}` and `{%var.amount}`.

**Rationale**: no test or page depends on these two lines beyond the actions themselves.

## R12. Facts the design relies on

Run, through the real coordinator, template engine and subscriptions, with their logic unchanged:

```text
'Order o1 total 9.5 [INFO] orders' var=OrderCompletedEvent typed=True level=INFO dump={'order_id': 'o1', 'total': 9.5}
```

A logger subscribed to `Channel.business` received the line, and one subscribed to `Channel.debug` did not.

Run, the same eleven templates through a dictionary and through an event: ten gave the same answer, including colours, `|debug`, `{iif(...)}`, a nested path, an absent variable and a forbidden `_private` path. The eleventh is a property marked `@sensitive`, masked on an event (`'41*****'`) and absent from a dictionary. A plain field prints as it is in both forms.

Run, the real demo build with and without an event class loaded: 3,973,313 bytes and the same hash `94e5a291bca346eb`, with no mention of the class.

Read: `tests/examples/test_examples_run.py` runs every script under `examples/`, so the new chapter's scripts are covered with no change to it.
