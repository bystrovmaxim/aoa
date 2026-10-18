# Adversarial evidence — US1, the declaration-time shape

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T013 | **Date**: 2026-10-18

A check written after the fix that passes on both versions proves nothing. So each validator was
disabled in turn, the test file was run, and the failures were compared with the tests the
validator is supposed to serve. The code was restored after each break, and the full suite was
re-run to confirm the restoration.

## Break 1 — `validate_names` returns before comparing

The break, inserted at the top of the function body in
`packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py`:

```python
    return  # ADVERSARIAL BREAK: names are not checked
    expected = _expected_parameters(contract, func)
    actual = tuple(inspect.signature(func).parameters)
```

```bash
.venv/bin/python -m pytest \
  packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_signature_names.py -q
```

```text
9 failed, 7 passed in 0.07s
```

The nine that failed are exactly the nine the name rule serves — five in `TestTheNamesInOrder`
(four decorators plus the message naming the declaration), three in `TestTheContextParameter`
(both directions, for summary and regular), and one more name case. The seven that still passed
are the four positional/default cases and the three "still passes" cases: a validator that stops
checking names does not fail the positional tests, which is what "fails alone" means here.

## Break 2 — `validate_positional` returns before checking

```python
    return  # ADVERSARIAL BREAK: position and defaults are not checked
    passed = ", ".join(contract.parameters)
    signature = inspect.signature(func)
```

```text
4 failed, 12 passed in 0.06s
```

The four are exactly `TestASignatureThatIsCalled`: keyword-only, `*args`, `**kwargs` and a default
on a value the pipeline supplies. The twelve name and acceptance tests kept passing.

## Restoration

```bash
.venv/bin/python -m pytest packages/aoa-action-machine/tests -q
```

```text
2577 passed in 13.04s
```

```bash
.venv/bin/python -m ruff check packages/
.venv/bin/python -m mypy packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/
```

```text
All checks passed!
Success: no issues found in 7 source files
```

## What the two breaks do not show

- They do not show that the *message* is right — the assertions on the fragments in
  `contracts/refusals.md` do that, and they are part of the same file.
- They do not show that the rule holds for the repository's own declarations: that is the corpus
  scan (`evidence/corpus-baseline.md`) and the suite, not this pass.

## What the pass changed in the tree, incidentally

The suite could not run at all while the repository's own fixtures still violated the rule: a
declaration refused at class creation breaks the import of the module that holds it. So the `.py`
half of US5 (`T033`) was pulled forward, as the plan's MVP note predicted — 61 declarations under
`packages/` were migrated, of which 43 by codemod (annotations and returns) and 18 by renaming a
parameter in place (`p, s, b, c`; `_params`; `_ctx`). The 19 deliberate refusals stayed wrong;
their six expected messages moved from "must accept N parameters" to the order the contract
names, and that is the only change in assertions the pass required.
