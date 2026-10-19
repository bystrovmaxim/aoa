# Implementation Plan: A role's mode is refused where it is declared, not where it is read

**Branch**: `feature/issue-233-role-mode-at-declaration` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-role-mode-declaration/spec.md`

## Summary

`@role_mode(mode: RoleMode)` has the annotation and no check: `@role_mode("alive")` is accepted, the string is written into `_role_mode_info`, and the first reader — `RoleMode.declared_for`, reached from `@check_roles` or from the access check — is what refuses, naming the value but not one thing that would have worked. A role nobody reads is never refused at all. Measured on this tree: the class is created, the metadata holds `'alive'`, and `RoleModeDeclarationError: Role ViewerRole has invalid _role_mode_info['mode']: 'alive'.` arrives from the reader.

The change adds the membership check where the mode is declared, and keeps every existing guard where it is:

1. **The set check, in the returned decorator, before the metadata is written.** The argument must be one of the four `RoleMode` members; anything else raises `RoleModeDeclarationError` naming the role, the value received and all four members in enum order. It fires during the import of the declaring module, with the class unbound, no graph assembled and no call served.
2. **The missing-parentheses check, in the decorator's own call.** `@role_mode` without parentheses hands the class over where the mode belongs; today that binds the class name to a function and fails later as `TypeError: issubclass() arg 1 must be a class`. It gets its own sentence, the same error class, and the same list.
3. **Nothing else moves.** `declared_for` keeps both of its refusals with their wording; `UNUSED`/`DEPRECATED`/`SILENCED` stay rules of `@check_roles` and the access check; the enum, the metadata key and the annotation are untouched. The public vocabulary does not grow.

The corpus does not move either: all 69 declaration sites already pass a member (59 `ALIVE`, 7 `SILENCED`, 2 `DEPRECATED`, 1 `UNUSED`), so the closing run is the proof that nothing existing is refused. One test module is added, the reference page gains the invariant, and a script-plus-notebook pair shows the refusal runnable.

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python = ">=3.12"`), eight packages under `packages/`.

**Primary Dependencies**: none new. The check is `isinstance`; the allowed list is derived from the enum with `", ".join(member.name for member in RoleMode)`.

**Storage**: N/A — declaration-time metadata on a class, not persisted state. The graph JSON schema is unchanged.

**Testing**: `pytest` (`packages/aoa-action-machine/tests/`), plus the closing run `bash scripts/run_checks_with_log.sh` (ruff, mypy, pylint, boundaries, metadata, build, vulture, radon, all suites). Verification is adversarial, per `AGENTS.md`: each new test is proved by breaking the code the way it must catch, confirming it fails alone, and restoring.

**Target Platform**: the eight Python packages; no server, no CLI, no adapter surface changes.

**Project Type**: library monorepo — one package changes (`aoa-action-machine`); the demo, the adapters and the examples consume it unchanged.

**Performance Goals**: no measurable cost. The check runs once per role class, at import; there is no run-time path — access checks keep calling `declared_for`, unchanged.

**Constraints**: no new dependency; the closing check run must end green; the edited modules keep their principle-III headers; the public function gets an AI-CORE block (principle IV); every new symbol gets a one-line docstring (principle V); all text in English (principle II); nothing is committed without the maintainer's instruction (principle I).

**Scale/Scope**: 1 decorator module edited, 1 exception module edited (block and docstring, class unchanged), 1 new test module, 1 reference-page bullet with its Russian draft beside it, 1 example pair (script + notebook), 1 changelog article. 69 declaration sites examined; 0 edited.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | How this plan satisfies it |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, PR or merge unless instructed in the current conversation | Four phases; each becomes a commit only on instruction. Nothing here ships on its own initiative. |
| II. English in commits and code | Every message, comment, docstring and refusal text in English | Both refusal messages are English; the code touched is already English. |
| III. Module headers | Path on line 1, title docstring, `═`-ruled `PURPOSE` / `ARCHITECTURE / DATA FLOW` | `role_mode_decorator.py` already carries the header and is edited in place; the function's docstring gains the rule inside the existing `COMPONENTS`/`EXAMPLES` text rather than a new section. The exception module keeps its path line and one-line docstring, widened in place. |
| IV. AI-CORE blocks | Public class or module-level function carries `ROLE`/`CONTRACT`/`INVARIANTS` | `role_mode` (public module-level function) and `RoleModeDeclarationError` (public class) each get a block; 7 of the 55 exception modules already carry one, `missing_check_roles_error.py` among them, so the shape follows the family (research R6). |
| V. Short docstrings | One line with a period on every class, function, method | The new private helper and the new test methods each get one; the widened exception docstring states the cause in one paragraph. |
| VI. The last three steps | Check run to zero, then documentation, then changelog — exactly three reserved tasks | Phases 2, 3 and 4 are those three steps, in that order, and no earlier task absorbs them. The examples are written inside the documentation step, as VI.5 requires, and executed while written (VI.6). |

**Violations requiring justification**: none. The two judgement calls — a second check for the bare form, and a new example pair instead of extending the silenced-role one — are argued in [research.md](./research.md) and repeated in Complexity Tracking.

**Re-checked after Phase 1 design**: unchanged. The design added no dependency and no public name; it edits one module, one docstring, one test tree, one page, one example pair and the changelog.

## Project Structure

### Documentation (this feature)

```text
specs/011-role-mode-declaration/
├── plan.md              # This file
├── research.md          # Phase 0 — the decisions and the probes
├── data-model.md        # Phase 1 — the enum, the metadata, the refusals as data
├── quickstart.md        # Phase 1 — how to verify by hand
├── contracts/
│   ├── declaration-contract.md   # What @role_mode accepts and stores
│   └── refusals.md               # The two refusals, word for word
├── evidence/
│   ├── scan_role_mode_calls.py   # 69 calls, 4 placeholders, 0 non-members
│   └── probes/                   # the message shape and a mypy probe
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── intents/role_mode/role_mode_decorator.py   # the set check, the bare-form check, an AI-CORE block
│   └── exceptions/role_mode_declaration_error.py  # AI-CORE block and a widened docstring, class unchanged
└── tests/action_machine/
    ├── intents/role_mode/
    │   └── test_role_mode_decorator_invariants.py # NEW — the feature's tests
    └── intents/check_roles/test_check_roles_class_roles.py  # untouched; its smoke test stays green

docs/reference/intents-and-invariants.md           # the invariant, under "Mandatory roles"
docs/CHANGELOG.md                                  # one article, dated 2026-10-19
examples/step_03_authorization_and_roles/
├── 17_a_wrong_role_mode.py                        # NEW — the accepted form and the refusals, runnable
└── 17_a_wrong_role_mode.ipynb                     # NEW — the same case, step by step
```

**Structure Decision**: the change lives in the package that owns the declaration (`aoa-action-machine`) and in the two carriers of its documentation (`docs/reference` and the step-03 example pair, which already owns role modes). No new package, no new layer, no shared helper: the check is a few lines inside the decorator it belongs to.

## Phases

Four phases; one phase, one commit, each leaving the tree green.

1. **The check and its refusals.** The set check and the missing-parentheses check in `role_mode_decorator.py`, the `_ALLOWED_MODES` constant, the AI-CORE blocks on `role_mode` and on `RoleModeDeclarationError` (whose docstring is widened), and `test_role_mode_decorator_invariants.py` covering the four accepted members, every refusal kind, the bare form, the message content, the no-metadata-on-refusal rule and `declared_for`'s two guards. Each test is proved adversarial before the phase ends.
2. **The check run.** `bash scripts/run_checks_with_log.sh` to zero, with the two accepted remarks left alone.
3. **The documentation.** The invariant under `## Mandatory roles` in `docs/reference/intents-and-invariants.md` — the four members, the wrong argument refused at the declaration, the context rules that stay with their consumers — and the example pair `17_a_wrong_role_mode.py` / `.ipynb`, written once the code is settled and executed while written.
4. **The changelog.** One article at the top of `docs/CHANGELOG.md` about what this created: a wrong role mode is now visible where it is declared, with the four names in the message.

Phases 2, 3 and 4 **are** the three reserved tail steps of principle VI — check run, documentation, changelog, in that order. `tasks.md` reserves them as exactly three tasks, and no task in phase 1 may absorb them.

## Complexity Tracking

| Decision | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| Two checks in one function rather than one | The bare form (`@role_mode`) never reaches the returned decorator at all — `X = role_mode(X)` binds the class to the inner function — so one check cannot see both mistakes | A single set check in `decorator(cls)` leaves `@role_mode` silently turning a role into a function and failing later as `TypeError: issubclass() arg 1 must be a class`, which is the failure this change exists to remove |
| A new test module rather than extending `test_check_roles_class_roles.py` | The new module judges the decorator's own invariants; that module judges `@check_roles` and already carries a `@role_mode` smoke test | Extending it would mix two subjects and grow a large module for one decorator |
| A new example pair (`17_…`) rather than extending `16_silenced_role` | `16` is about what silencing does to access; the refusal is about the declaration's shape | Extending `16` would make one example answer two questions, and constitution VI.5 asks a case to appear as script and notebook — a new pair satisfies it without blurring the old case |
