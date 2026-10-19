# Feature Specification: A role's mode is refused where it is declared, not where it is read

**Feature Branch**: `feature/issue-233-role-mode-at-declaration`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/233 — `@role_mode("alive")` is accepted in silence: the decorator writes whatever it is handed into the class metadata. The mistake surfaces later, during assembly, in a message that does not name the value received. After this change the argument is refused when the decorator is applied, naming what arrived and the four members it would have accepted."

## Context: what `@role_mode` does today, measured

`role_mode(mode: RoleMode)` carries the annotation and no check. On the tree as it stands — measured on 2026-10-19, not taken from the issue:

```python
@role_mode("alive")
class Viewer(RoleModeIntent):
    pass

Viewer._role_mode_info          # {'mode': 'alive'}  — accepted, verbatim
RoleMode.declared_for(Viewer)   # RoleModeDeclarationError:
                                # Role Viewer has invalid _role_mode_info['mode']: 'alive'.
```

Three things follow from that: the class is created, the metadata holds a `str`, and the refusal arrives from the first reader rather than from the declaration. That reader is `RoleMode.declared_for`, which the assembly reaches through `@check_roles` (`_validate_required_role_modes`) and the access check reaches through `_active_user_roles` and `_user_role_grants_requirement` (`intents/access_control/roles.py:181,188`). Two consequences matter for this feature:

- **The message names the value but not the alternatives.** A developer who reads `invalid _role_mode_info['mode']: 'alive'` still has to find `RoleMode` to learn what would have been right.
- **A role nobody requires and nobody checks is never refused at all.** The class imports, the metadata carries a string, and no code path ever asks.

The set the decorator means is closed, and the four members are not interchangeable — each is read by a different consumer and means a different thing:

| Member | String value | What it means | Who reads it and what it does |
| --- | --- | --- | --- |
| `ALIVE` | `"alive"` | the role is in force | nothing blocks it; `ApplicationRole`, `SystemRole`, `GuestRole`, `AnyRole` and the demo roles are declared this way |
| `DEPRECATED` | `"deprecated"` | the role is outdated but still works | `@check_roles` raises a `DeprecationWarning` and accepts the requirement anyway (`_validate_required_role_modes`); the demo's `DeprecatedRole` (in `model/roles/legacy.py`) is the example |
| `SILENCED` | `"silenced"` | the role is switched off | the access check drops the user's role from the active set and it grants nothing (`roles.py:181,188`) |
| `UNUSED` | `"unused"` | the role is kept in the code but is not used | `@check_roles` refuses to require it, with `RoleSpecTypeError` |

**The boundary this feature does not move.** Belonging to the set is not the same as being apt in every context. `UNUSED` cannot be required, `DEPRECATED` warns, `SILENCED` grants nothing — those rules live at the consumers and stay there. The decorator learns one thing only: that its argument is one of the four.

**The corpus.** 69 declaration sites in the repository, measured by scanning `packages/`, `examples/`, `tests/` and `docs/` on 2026-10-19: 59 `RoleMode.ALIVE`, 7 `RoleMode.SILENCED`, 2 `RoleMode.DEPRECATED`, 1 `RoleMode.UNUSED` — 64 in `.py`, 2 in `docs/tutorials/step-03-authorization-and-roles.md`, 2 in its Russian draft beside it, 1 in the example notebook `examples/step_03_authorization_and_roles/16_silenced_role.ipynb`. No site passes a string or any other non-member value. The issue says 67; the scan says 69, and the difference is measurement, not work. Four further occurrences write `@role_mode(...)` or `@role_mode(RoleMode.…)` as a placeholder inside prose and are not calls.

## Clarifications

### Session 2026-10-19 — decisions taken while writing this specification

- **The refusal happens at the decorator's application to the class, and it names the role.** The order was measured, not assumed: the decorator expression is evaluated first (`role_mode("alive")`), then the class body runs, then the decorator is applied to the finished class. Refusing at the application therefore costs one detail — the class body has run by then — and buys the one thing a reader needs: the refusal can say which role it is about (`Role ViewerRole`), the way `declared_for` already does. The class is still not bound under its name, no operation assembles and no call is served, so the mistake is still refused during the import of its own module. The alternatives are recorded: refusing in the argument expression is a step earlier but cannot name the role, and validating in `declared_for` — which is what happens today — is the defect itself, because it refuses a role only if something reads it.
- **The refusal keeps the error name the codebase already has.** `RoleModeDeclarationError` is public, exported, subclass of `TypeError`, and already means "a role carries no usable `RoleMode` metadata". Its docstring widens to cover the argument the decorator was handed; no new public name appears, and a caller that already catches this error for a role keeps catching it.
- **The argument is checked, not coerced.** `@role_mode("alive")` is refused rather than read as `RoleMode.ALIVE`. A compatibility reading would give the closed set a second spelling, and the second spelling is exactly the mistake — no site in the repository uses it.
- **The allowed set is the four members, in the order the enum declares them.** `RoleMode` is an `Enum` of four, and the refusal lists `ALIVE, DEPRECATED, SILENCED, UNUSED` — the enum's own definition order, stable across runs, never a set's iteration order. The list is the message's obligation, not a separate constant the message is generated from by accident: three of four would fail the acceptance test.
- **`declared_for` keeps every check it has.** It stops being the only guard; it does not stop being a guard. A role class with no metadata anywhere in its MRO, or with metadata whose `mode` is not a `RoleMode` (written by other means than the decorator, or by an older version of it), is refused there exactly as today.
- **The context rules are not moved into the decorator.** `UNUSED`/`DEPRECATED`/`SILENCED` remain rules of `@check_roles` and the access check, with the errors and warnings they raise today. Moving them would make the decorator refuse a declaration that is well formed but unsuitable — a different rule, and a different moment.
- **The decorator's other checks keep their order and their names.** A non-class target is still refused with `DecoratorTargetError` before the mode is judged — the target is known at the first line of the application and the order that exists today is not rearranged; a decorated class that is not a `RoleModeIntent` is not refused by the decorator today and is not made a refusal here — `declared_for` names it with `DecoratorArgumentTypeError` when something reads it. The one addition beside the argument check is the bare form (`@role_mode` without parentheses), decided below: it is the same mistake as a wrong argument, arriving by another road.
- **Nothing about `RoleMode` changes.** The enum stays an `Enum` of four with the same four string values, the metadata keeps its `{"mode": ...}` shape and its key, and the annotation `mode: RoleMode` stays as it is.

### Session 2026-10-19 — clarification

- Q: Where should the check stand — in the `role_mode("alive")` call, before the class body runs, or in the decorator's application to the finished class? → A: **At the application to the class.** It is still import time, the class is still unbound, and no graph is assembled, so the moment the issue asks for is kept; the difference is that the refusal can name the role it is about, as `declared_for` already does. The measured order — argument, class body, application — is recorded in the decision above, because the first draft of this specification stated the order wrongly.
- Q: Should `RoleMode.declared_for`'s message — the refusal for metadata written in spite of the decorator — gain the same list of four members? → A: **No, it keeps its wording.** The role and the value are already named there, the path becomes rare once the decorator refuses the argument, and changing the text would churn existing tests for a case the repository does not contain. One list, in the one refusal a developer can actually reach.
- Q: Should `@role_mode` written without parentheses be refused as well? → A: **Yes.** Measured on the tree: `@role_mode` binds the class name to the decorator's inner function, and the mistake surfaces much later as `TypeError: issubclass() arg 1 must be a class` — the same late, elsewhere, unexplained failure this feature exists to remove, produced by the same wrong argument arriving by another road. The refusal says that the parentheses are missing and names a `RoleMode` member as what belongs inside them. It stays narrow: the decorator still does not check that its target is a `RoleModeIntent`, which `declared_for` continues to do.

## User Scenarios & Testing *(mandatory)*

The readers of this feature are a developer writing a role class, a developer reading the refusal they just got, and the maintainer of the demo model, whose roles are the examples the tutorials walk through.

### User Story 1 - A wrong mode is refused where it is written (Priority: P1)

A developer writes `@role_mode("alive")` — the string is what the table in the documentation shows, and the annotation on the decorator is invisible while typing. Today the class is created and the metadata holds a string; if the role is required somewhere, assembly dies with `RoleModeDeclarationError: ... invalid _role_mode_info['mode']: 'alive'`, which names the value but not one thing that would have worked. If the role is not required anywhere, nothing ever says anything.

After this change the decorator itself refuses the argument, in the same file, when the module is imported — and the refusal says which role, which value arrived and which four would have been accepted.

**Why this priority**: this is the defect. Every other story is either the same rule seen from the accepted side, or a protection that must survive the change.

**Independent Test**: apply the decorator with a string, a number, `None`, a member of a different `Enum` and an arbitrary object, and once without parentheses; each must fail while the module is imported, naming the role and the value, and no class with `_role_mode_info` must come out of it.

**Acceptance Scenarios**:

1. **Given** `@role_mode("alive")` on a role, **When** the module is imported, **Then** `RoleModeDeclarationError` is raised at that class statement, the message names the role, contains `'alive'` and the four member names `ALIVE`, `DEPRECATED`, `SILENCED`, `UNUSED`, and no class carrying the metadata is created.
2. **Given** `@role_mode(RoleMode.ALIVE.value)` — the same string reached the other way round, **When** the module is imported, **Then** it is refused identically: the value's origin does not matter, only what it is.
3. **Given** `@role_mode(42)`, **When** the module is imported, **Then** it is refused, and the message shows `42` — a number that is not even a string the enum could carry.
4. **Given** `@role_mode(None)`, **When** the module is imported, **Then** it is refused, and the message shows `None` in a form that cannot be read as the string `"None"`.
5. **Given** `@role_mode(object())`, **When** the module is imported, **Then** it is refused, and the message shows the object's reproduction rather than an empty or generic phrase.
6. **Given** a member of another `Enum` whose value happens to be `"alive"`, **When** the module is imported, **Then** it is refused: the set is this enum's members, not values equal to theirs.
7. **Given** a wrong argument passed by keyword — `@role_mode(mode="alive")` — **When** the module is imported, **Then** it is refused the same way as the positional form.
8. **Given** a correct declaration, **When** the module is imported, **Then** nothing is raised and the metadata holds the member itself.
9. **Given** `@role_mode` written without parentheses, **When** the module is imported, **Then** `RoleModeDeclarationError` names the role, says the parentheses are missing and names a `RoleMode` member as what belongs inside them — the mistake is not left to a later `issubclass()` failure.

---

### User Story 2 - All four members are accepted and stored as given (Priority: P2)

A developer declares a role with any of the four modes — alive, deprecated, silenced, unused — and reads the metadata back. The check must not narrow what was always valid: all four are valid arguments, and what the decorator stores must be the object it was given, not a copy, not a string, not a normalised surrogate.

**Why this priority**: a check that refuses the wrong thing is worse than no check. Four members and 69 call sites sit on the accepted side, and none of them may move.

**Independent Test**: declare one role per member and assert, one test per member, that the metadata entry is that member — compared by identity, not by value — and that the decorator returns the class unchanged.

**Acceptance Scenarios**:

1. **Given** `@role_mode(RoleMode.ALIVE)`, **When** the class is defined, **Then** `_role_mode_info["mode"]` is `RoleMode.ALIVE`.
2. **Given** `@role_mode(RoleMode.DEPRECATED)`, **When** the class is defined, **Then** the metadata holds `RoleMode.DEPRECATED` and the role is otherwise treated as it is today.
3. **Given** `@role_mode(RoleMode.SILENCED)`, **When** the class is defined, **Then** the metadata holds `RoleMode.SILENCED`.
4. **Given** `@role_mode(RoleMode.UNUSED)`, **When** the class is defined, **Then** the metadata holds `RoleMode.UNUSED`.
5. **Given** any accepted member, **When** the decorated class is compared with the class the decorator returns, **Then** it is the same class object — the decorator attaches metadata and does nothing else.
6. **Given** the 69 declaration sites of the repository, **When** their modules are imported, **Then** none is refused and their tests stay green.

---

### User Story 3 - The protections that existed stay (Priority: P3)

A role class can be created without the decorator at all, and a metadata entry can be wrong for reasons this check does not see — an attribute set by hand, a mode written by another mechanism. The accessor that reads the mode has always refused both, and the three context rules have always lived with their consumers. None of that is removed by adding a check upstream.

**Why this priority**: it is the invariant the change could quietly break. A developer who moves the rule may "simplify" `declared_for` and find, a release later, that a role without a mode grants nothing instead of being refused.

**Independent Test**: create a role subclass with no decorator, and one whose `_role_mode_info["mode"]` was overwritten with a string; both must still be refused by `declared_for`. Then re-run the existing tests for the three context rules and confirm the same errors and the same warning.

**Acceptance Scenarios**:

1. **Given** a `RoleModeIntent` subclass with no `@role_mode` anywhere in its MRO, **When** `RoleMode.declared_for` is asked for its mode, **Then** `RoleModeDeclarationError` says the class has no `_role_mode_info`, exactly as today.
2. **Given** a role whose `_role_mode_info["mode"]` was replaced with `"alive"` after the declaration, **When** `declared_for` is asked for its mode, **Then** it is refused, exactly as today.
3. **Given** a role marked `RoleMode.UNUSED`, **When** `@check_roles` requires it, **Then** `RoleSpecTypeError` is raised as today.
4. **Given** a role marked `RoleMode.DEPRECATED`, **When** `@check_roles` requires it, **Then** a `DeprecationWarning` is raised and the requirement is accepted as today.
5. **Given** a role marked `RoleMode.SILENCED`, **When** access is checked for a user holding it, **Then** it grants nothing as today.

---

### Edge Cases

- **A string equal to a member's value.** `"alive"`, `"deprecated"`, `"silenced"`, `"unused"` are all refused. The values are what the enum exposes; the members are what the decorator accepts.
- **A member of another enum.** An `Enum`, `IntEnum` or `StrEnum` member that carries the same string value is refused. Membership in `RoleMode` is what the decorator asked for, and `RoleMode.ALIVE` is not equal to a member of another class — measured, not assumed: `RoleMode.ALIVE == Other.ALIVE` is `False`, and a `StrEnum` member is not an instance of `RoleMode`.
- **`None`, numbers, callables, instances.** Refused with the same error and the same list; the message shows what arrived with its reproduction, so `None` and `"None"` cannot be confused.
- **The same class decorated twice with two valid modes.** The order of decorators decides which mode wins, as it does today: the outer application runs last and overwrites the entry. The argument check applies to each application; the result is unchanged.
- **A role that inherits its mode.** A subclass without its own decorator reads its parent's mode through `declared_for` — today's behaviour, untouched by this feature. A subclass that declares its own mode is checked on its own argument.
- **A decorated class that is not a role.** The target is judged first, with `DecoratorTargetError`, and the mode second: a manual application to something that is not a class still reports the target, and the order the decorator has today is not rearranged. A class that is not a `RoleModeIntent` is not judged by the decorator at all — `declared_for` names it when something reads it.
- **The decorator without parentheses.** `@role_mode` binds the class name to the decorator's inner function and the failure shows up much later, as `issubclass() arg 1 must be a class`; this is the same wrong argument arriving by another road, and it is refused with the same error and a message about the missing parentheses. The class is not bound in either version of the mistake.
- **A placeholder in prose.** `@role_mode(...)` and `@role_mode(RoleMode.…)` appear in docstrings and pages as text, never as calls; they are not refused and need no change.
- **The message itself.** Four names, one value, no set iteration order, and the decorator's name so that a reader who has several decorators on the class knows which one spoke.

## Requirements *(mandatory)*

### The refusal at the declaration

- **FR-001**: `@role_mode` MUST refuse an argument that is not a member of `RoleMode` at the decorator's application to the class — while the statement declaring the role is executed, before `_role_mode_info` is written, during the import of the module that declares the role. The class exists by then; its name is not bound, no operation is assembled and no call is served.
- **FR-002**: The refusal MUST be `RoleModeDeclarationError`, the error the framework already raises for a role that carries no usable mode metadata; no new public error name is introduced, and a caller catching this error for roles keeps catching the new refusal.
- **FR-003**: The message MUST contain the value received, in a form that distinguishes `None` from `"None"` and `42` from `"42"`, and MUST contain all four member names `ALIVE`, `DEPRECATED`, `SILENCED`, `UNUSED` in that order.
- **FR-004**: The message MUST name the decorator and the role it was applied to, by the class's qualified name, so that a module with several role classes — and a class carrying several decorators — leaves no ambiguity about which declaration was refused.
- **FR-005**: The check MUST run before the metadata is written: a refused argument MUST NOT leave `_role_mode_info` behind on any class.
- **FR-006**: The refusal MUST happen in the decorator, not in `RoleMode.declared_for`: a test that imports the module and never assembles anything MUST see it.

### The closed set

- **FR-007**: Exactly the four `RoleMode` members MUST be accepted, and nothing else — not the strings they carry, not values equal to those strings, not members of another enum, not `None`, not a number, not an arbitrary object.
- **FR-008**: An accepted argument MUST be stored in `_role_mode_info["mode"]` as the object it was — the same member, comparable by identity — and the metadata's key and shape MUST stay `{"mode": ...}`.
- **FR-009**: The decorator MUST otherwise behave as today: it attaches the metadata to the class it is given and returns that same class unchanged.

### The protections that stay

- **FR-010**: `RoleMode.declared_for` MUST keep both refusals it has today — a class with no `_role_mode_info`, and a metadata entry whose `mode` is not a `RoleMode` — with their current error type, their current wording, and messages that still distinguish the two cases. The list of four belongs to the decorator's refusal alone.
- **FR-011**: The context rules MUST NOT move into the decorator: `UNUSED` required through `@check_roles` still raises `RoleSpecTypeError`, `DEPRECATED` still raises a `DeprecationWarning` and is still accepted, `SILENCED` still grants nothing.
- **FR-012**: A declaration that complies MUST behave identically: the same assembly, the same answers, the same events, the same logs, and the same warnings as before the change.
- **FR-013**: No other argument, target or metadata rule about `@role_mode` may change as a side effect — apart from the missing parentheses of FR-019, the non-class target keeps `DecoratorTargetError`, the non-`RoleModeIntent` target keeps being refused by `declared_for` alone, and the annotation `mode: RoleMode` stays.

### The corpus and the tests

- **FR-014**: The 69 declaration sites of the repository — in the modules under `packages/`, `examples/` and `tests/`, and in the page and notebook that show the decorator — MUST keep passing a member, their modules MUST keep importing, and their tests MUST stay green; none of them needs editing for the argument check, and any that does is a mistake in the check rather than in the site.
- **FR-015**: The four prose placeholders (`@role_mode(...)`, `@role_mode(RoleMode.…)`) MUST stay as they are: they are text, not calls, and the feature neither rewrites them nor gives them a meaning.
- **FR-016**: The tests MUST cover one acceptance per member, every refusal kind of User Story 1 — a member's string, the same value reached through `.value`, a number, `None`, an arbitrary object, a member of another enum, the keyword form and the missing parentheses — and the two refusals of `declared_for`; each refusal MUST be demonstrated by failing without the check rather than by asserting on a message alone. The three context rules are covered by the tests that already own them — `test_role_checker_pr2.py` for `UNUSED` and `DEPRECATED`, `test_roles.py` for `SILENCED` — and this change MUST leave those files unedited and green rather than duplicate their cases.

### Documentation

- **FR-017**: `docs/reference/intents-and-invariants.md` MUST state the invariant in the roles section: the mode is part of a role's declaration, it is one of exactly four members, and a wrong one is refused where it is written; the context rules stay with their consumers and the page says so.
- **FR-018**: The changelog MUST carry one article about what the change gives the reader — a wrong role mode is now visible at the place it is declared — with no per-file account and no technical detail beyond the sentence a user needs.

### The missing parentheses

- **FR-019**: `@role_mode` written without parentheses — the class arrives where the mode belongs — MUST be refused with `RoleModeDeclarationError` during the import, before the class name is bound to anything; the message MUST name the role, say that the parentheses are missing, and name a `RoleMode` member as the argument. A later `TypeError` from `issubclass()` MUST NOT be how this mistake is reported.
- **FR-020**: The refusal for the bare form MUST carry the same list of four members as every other argument refusal (FR-003), so a developer who forgets the parentheses reads one message, not two different ones.

### Key Entities

- **Role mode**: the lifecycle classification of a role class — one of four members, decided once at the declaration and stored on the class. It is what this feature judges.
- **Role**: a class that marks a capability in the access check. Its mode decides nothing by itself: what the mode means is decided by the consumer that reads it.
- **Refusal**: the answer to an argument that is not in the closed set. It names the role, the value received, the four members and the decorator; it is the feature's only user-visible output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every non-member argument listed in the acceptance scenarios is refused while the module is imported, with no graph assembled and no call served — 100 % of them, including the bare form that forgets the parentheses, in a test that fails if the refusal moves back to assembly or turns into a later `issubclass()` failure.
- **SC-002**: Each refusal names the role, the value received and all four members; a reader who has never opened the package can fix the declaration from the message alone.
- **SC-003**: All 69 declaration sites of the repository pass a member, their modules import unchanged and the closing check run is green, so no role in the corpus is refused by the new rule.
- **SC-004**: An operation or access check that worked before the change works identically after it — same answers, same events, same logs, same `DeprecationWarning` for a deprecated role.
- **SC-005**: The public vocabulary does not grow: `RoleModeDeclarationError` is still the only error a wrong mode raises, and the error a caller catches for roles today still catches it.

## Assumptions

- The closed set is `RoleMode` itself, verified in the code rather than taken from the issue: four members, `ALIVE`, `DEPRECATED`, `SILENCED`, `UNUSED`, in that definition order, with the string values `"alive"`, `"deprecated"`, `"silenced"`, `"unused"`.
- One claim in the issue did not survive measurement and is recorded here: `BaseRole` is not decorated with `@role_mode` — it carries `@exclude_graph_model` and is never asked for a mode — while `ApplicationRole`, `SystemRole`, `GuestRole`, `AnyRole` and the demo roles are declared `ALIVE`. The count of call sites is 69, not 67.
- The moment of the refusal is the decorator's call. Statements in the class body have already run by then; this is the earliest moment the argument exists, and it is what "at the declaration" can mean for a decorator argument.
- The error's docstring is widened rather than duplicated: one name for "a role's mode is not usable", with the cause (missing, corrupted, or never a member) in the message.
- The reference page is updated, not rewritten, and no new page is written: the repository's rule is that documentation ships with the change it describes, not that every change grows the documentation.
- The code and its tests are one phase and one commit; the three tail steps of principle VI — the check run, the documentation, the changelog — follow as three further commits in that order, so the change is four phases in total, not one.
