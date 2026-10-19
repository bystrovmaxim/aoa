# Quickstart — verifying the role-mode refusal by hand

**Feature**: `specs/011-role-mode-declaration` | **Date**: 2026-10-19

Everything below runs from the repository root with the repository's own environment (`.venv/`, or `uv run --extra dev <cmd>`). The contracts are in [contracts/declaration-contract.md](./contracts/declaration-contract.md) and [contracts/refusals.md](./contracts/refusals.md); this page only sequences the runs.

## 1. The corpus claim still holds

```bash
python3 specs/011-role-mode-declaration/evidence/scan_role_mode_calls.py
```

Expected: `real calls: 69 {...}`, `placeholders in prose: 4`, `arguments that are neither a member nor a known placeholder: 0`, exit status 0. If the first number grows, a new declaration was added — it must pass a member, or the check will refuse it.

## 2. The refusal fires where it is written

Save as `/tmp/role_mode_case.py` and run it with the repository environment:

```python
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.role_mode import RoleMode, role_mode

try:
    @role_mode("alive")
    class ViewerRole(BaseRole):
        name = "viewer"
        description = "Can read the catalog"
except Exception as error:
    print(type(error).__name__, "->", error)

try:
    @role_mode
    class BareRole(BaseRole):
        name = "bare"
        description = "Forgot the parentheses"
except Exception as error:
    print(type(error).__name__, "->", error)

@role_mode(RoleMode.ALIVE)
class GoodRole(BaseRole):
    name = "good"
    description = "Declared correctly"

print("accepted:", GoodRole._role_mode_info["mode"] is RoleMode.ALIVE)
```

Expected: two `RoleModeDeclarationError` lines, each naming the role, the value (or the class), the four members and, for the second, the missing parentheses; then `accepted: True`. No `issubclass()` `TypeError` anywhere.

## 3. The suite

```bash
.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/intents/role_mode/ -v
.venv/bin/pytest packages/aoa-action-machine/tests/ -q
```

The first is the feature's own module (`test_role_mode_decorator_invariants.py`): four accepted members, the refusal kinds, the bare form, the message content, the no-metadata-on-refusal rule and `declared_for`'s two guards. The second proves nothing else moved — in particular the context-rule tests, which this feature does not touch:

```bash
.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/scenarios/intents_with_runtime/test_role_checker_pr2.py \
                  packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py -q
```

## 4. Adversarial check (how the tests are proved to matter)

Each break is applied, the suite is run, the expected tests fail alone, and the code is restored:

| Break | Must fail | Must not fail |
| --- | --- | --- |
| restore the `cast` and delete the set check | every refusal test, at import of the test module | the accepted-member tests |
| move the check from `decorator(cls)` into `declared_for` | the "refused at import, no assembly" tests | the `declared_for` guard tests |
| drop the value from the message | the value-content assertions | the refusal-type assertions |
| print three members instead of four | the "all four, in order" assertion | the other message assertions |
| delete the missing-parentheses check | the bare-form test (which then sees an `issubclass()` `TypeError`) | the set-check tests |
| write `_role_mode_info` before the check | the no-metadata-on-refusal test | the rest |

## 5. The closing run

```bash
bash scripts/run_checks_with_log.sh
```

Expected: green, with the two remarks the constitution accepts (the Vite chunk-size advisory and LangGraph's pending deprecation) left in place. The log is appended to `archive/logs/check-all.txt`; `archive/` is outside Git.

## What a reader should be able to say afterwards

1. `@role_mode` takes one of four members, and a string is not one of them.
2. A wrong argument fails in the file where it is written, at import, before any graph exists.
3. The refusal names the role, the value received and all four members, so it can be fixed from the message alone.
4. `@role_mode` without parentheses is a mistake with its own sentence, not a later `issubclass()` failure.
5. Nothing about the four modes' meanings — deprecated, silenced, unused — moved.
