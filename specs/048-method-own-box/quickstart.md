# Quickstart: validating Every method of an action gets its own box

Run from the repository root.

## The tests

```bash
uv run --package aoa-action-machine --group dev pytest packages/aoa-action-machine/tests/action_machine/runtime/test_every_method_has_its_own_box.py -q
```

Expected: all pass, one rule case per kind of method, two for `@access_decide` (a normal run and `check_access_decide`).

## The case from the issue

```bash
uv run python examples/how_to/09_method_box.py
```

Expected: the handler writes `reserved=yes` and the action returns the handler's result. Before this work the same handler ends in `OnErrorHandlerError`.

## The adversarial breaks

Each break is one temporary edit, restored afterwards. The rule's test must fail in the named case and no other test may fail.

| # | Break | Must fail |
|---|---|---|
| 1 | Regular aspect: pass `""` as the method name | rule test, regular case |
| 2 | Summary aspect: pass `""` as the method name | rule test, summary case |
| 3 | Compensator: pass `""` as the method name | rule test, compensate case |
| 4 | Handler: pass `""` as the method name | rule test, on_error case |
| 5 | Check: `_decide` ignores `check_name` | rule test, both access_decide cases |
| 6 | Handler: pass an empty `BaseState()` | the handler's `state` test |
| 7 | Compensator: pass the current state instead of the snapshot | the compensator's `state` test |

## The check run

```bash
bash scripts/check_before_commit.sh
```

Expected: exit code 0.
